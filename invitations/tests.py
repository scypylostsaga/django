from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from invitations.models import Invitation, Schedule, Guest, Wish

User = get_user_model()


class InvitationTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password123")
        self.invitation = Invitation.objects.create(
            user=self.user,
            title="Emma & Liam Wedding",
            slug="emma-and-liam",
            event_type="wedding",
            hosts_or_celebrants="Emma Watson & Liam Hemsworth",
            event_date=timezone.now() + timedelta(days=20),
            venue_summary="Grand Palace, Paris",
            theme_color="#b45309",
            gift_bank_name="Chase",
            gift_account_number="123456789",
        )
        self.schedule = Schedule.objects.create(
            invitation=self.invitation,
            title="Solemnization",
            start_time=timezone.now() + timedelta(days=20),
            venue_name="Chapel",
        )
        self.guest = Guest.objects.create(
            invitation=self.invitation,
            name="Sophia Taylor",
            max_pax=2,
        )

    def test_public_invitation_view_and_opengraph(self):
        response = self.client.get(f"/invite/{self.invitation.slug}/?to=Sophia+Taylor")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Emma &amp; Liam Wedding")
        self.assertContains(response, "Sophia Taylor")
        self.assertContains(response, 'property="og:title"')
        self.assertContains(response, 'property="og:description"')
        self.assertContains(response, "Open Invitation")
        self.assertContains(response, "Counting Down To The Day")

    def test_submit_rsvp(self):
        response = self.client.post(
            f"/invite/{self.invitation.slug}/rsvp/",
            {
                "guest_name": "Sophia Taylor",
                "is_attending": "yes",
                "actual_pax": 2,
                "notes": "Looking forward to it!",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        self.guest.refresh_from_db()
        self.assertTrue(self.guest.is_attending)
        self.assertEqual(self.guest.actual_pax, 2)
        self.assertEqual(self.guest.notes, "Looking forward to it!")

    def test_submit_wish(self):
        response = self.client.post(
            f"/invite/{self.invitation.slug}/wishes/",
            {
                "sender_name": "Sophia Taylor",
                "attendance_status": "attending",
                "message": "Wishing you both endless love and bliss!",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        wish = Wish.objects.filter(invitation=self.invitation, sender_name="Sophia Taylor").first()
        self.assertIsNotNone(wish)
        self.assertEqual(wish.message, "Wishing you both endless love and bliss!")

    def test_dashboard_authenticated(self):
        self.client.login(username="testuser", password="password123")
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Emma &amp; Liam Wedding")

    def test_media_urls_fallback(self):
        # Without uploaded file, fallback to URL
        self.assertEqual(self.invitation.get_cover_image_url, self.invitation.cover_image_url)
        self.assertEqual(self.invitation.get_audio_url, "")

    def test_gdrive_url_normalization(self):
        # Test image conversion
        self.invitation.cover_image_url = "https://drive.google.com/file/d/1c244Qq5hbv8lwKhtjXTI5cjU7-3Bix8S/view?usp=drive_link"
        self.invitation.audio_url = "https://drive.google.com/file/d/1a2B3c4D5e6F7g8H9i0JkLmNoP/view?usp=sharing"
        self.invitation.save()

        self.assertEqual(
            self.invitation.get_cover_image_url,
            "https://lh3.googleusercontent.com/d/1c244Qq5hbv8lwKhtjXTI5cjU7-3Bix8S",
        )
        self.assertEqual(
            self.invitation.get_audio_url,
            "https://docs.google.com/uc?export=download&id=1a2B3c4D5e6F7g8H9i0JkLmNoP",
        )

    def test_gallery_upload(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        import io
        from PIL import Image

        self.client.login(username="testuser", password="password123")
        # Generate tiny 10x10 image in memory
        img = Image.new("RGB", (10, 10), color="pink")
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="JPEG")
        uploaded_image = SimpleUploadedFile("test_moment.jpg", img_bytes.getvalue(), content_type="image/jpeg")

        response = self.client.post(
            f"/invitations/{self.invitation.slug}/gallery/add/",
            {"image": uploaded_image, "caption": "Romantic sunset"},
        )
        self.assertEqual(response.status_code, 302)
        photo = self.invitation.gallery_photos.first()
        self.assertIsNotNone(photo)
        self.assertEqual(photo.caption, "Romantic sunset")
        self.assertTrue(photo.image.name.endswith(".jpg"))

        # Check public page renders the gallery
        public_resp = self.client.get(f"/invite/{self.invitation.slug}/")
        self.assertEqual(public_resp.status_code, 200)
        self.assertContains(public_resp, "Our Photo Gallery")
        self.assertContains(public_resp, "Romantic sunset")

    def test_auto_google_maps_generation(self):
        # Create schedule without map_url
        schedule = Schedule.objects.create(
            invitation=self.invitation,
            title="Reception Dinner",
            start_time=timezone.now() + timedelta(days=20, hours=4),
            venue_name="The Glass House",
            address="Uluwatu, Bali",
            map_url="",
        )
        self.assertTrue(schedule.map_url.startswith("https://www.google.com/maps/search/?api=1&query="))
        self.assertIn("The+Glass+House", schedule.map_url)
        self.assertIn("Bali", schedule.map_url)

    def test_cover_focus_roi(self):
        self.invitation.cover_focus_position = "50% 18%"
        self.invitation.save()
        resp = self.client.get(f"/invite/{self.invitation.slug}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "object-position: 50% 18%")
        self.assertContains(resp, "background-position: 50% 18%")

    def test_invitation_form_url_sanitization(self):
        from invitations.forms import InvitationForm

        self.invitation.cover_image = "invitations/covers/photo.jpg"
        self.invitation.save()

        # 1. blob: URL submitted when instance or cleaned_data has cover_image -> sanitized to ""
        form = InvitationForm(
            data={
                "title": "Test Sanitize",
                "slug": "test-sanitize",
                "event_type": "wedding",
                "hosts_or_celebrants": "A & B",
                "event_date": "2027-01-01T10:00",
                "theme_color": "#b45309",
                "font_family": "serif",
                "cover_image_url": "blob:http://127.0.0.1:8000/12345",
                "audio_url": "blob:http://127.0.0.1:8000/67890",
            },
            instance=self.invitation,
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["cover_image_url"], "")
        self.assertEqual(form.cleaned_data["audio_url"], "")

        # 2. Valid https URL -> preserved
        form2 = InvitationForm(
            data={
                "title": "Test Sanitize 2",
                "slug": "test-sanitize-2",
                "event_type": "wedding",
                "hosts_or_celebrants": "A & B",
                "event_date": "2027-01-01T10:00",
                "theme_color": "#b45309",
                "font_family": "serif",
                "cover_image_url": "https://example.com/photo.jpg",
                "audio_url": "https://example.com/audio.mp3",
            },
            instance=self.invitation,
        )
        self.assertTrue(form2.is_valid(), form2.errors)
        self.assertEqual(form2.cleaned_data["cover_image_url"], "https://example.com/photo.jpg")
        self.assertEqual(form2.cleaned_data["audio_url"], "https://example.com/audio.mp3")

    def test_invitation_edit_view_with_cover_image(self):
        self.client.login(username="testuser", password="password123")
        self.invitation.cover_image = "invitations/covers/photo.jpg"
        self.invitation.save()

        # Simulate edit form POST where Alpine or user sent relative /media/... path in cover_image_url
        response = self.client.post(
            f"/invitations/{self.invitation.slug}/edit/",
            {
                "title": "Emma & Liam Wedding (Updated)",
                "slug": "emma-and-liam",
                "event_type": "wedding",
                "hosts_or_celebrants": "Emma & Liam",
                "event_date": "2027-05-20T11:00",
                "venue_summary": "Paris",
                "cover_image_url": "/media/invitations/covers/photo.jpg",
                "cover_focus_position": "50% 30%",
                "theme_color": "#b45309",
                "font_family": "serif",
                "is_published": True,
            },
        )
        # Should succeed with redirect 302 to invitation_detail, not re-render 200
        self.assertEqual(response.status_code, 302)
        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.title, "Emma & Liam Wedding (Updated)")
        self.assertEqual(self.invitation.cover_focus_position, "50% 30%")
        self.assertEqual(self.invitation.cover_image_url, "")

    def test_cover_photo_zoom_level_and_scale(self):
        # Default zoom scale is 1.0 (100%)
        self.assertEqual(self.invitation.cover_zoom_level, 100)
        self.assertEqual(self.invitation.cover_zoom_scale, 1.0)

        # Set zoom to 150% (1.5x)
        self.invitation.cover_zoom_level = 150
        self.invitation.cover_focus_position = "50% 20%"
        self.invitation.save()
        self.assertEqual(self.invitation.cover_zoom_scale, 1.5)

        # Verify public page renders scale transform and zoom button
        resp = self.client.get(f"/invite/{self.invitation.slug}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "transform: scale(1.5)")
        self.assertContains(resp, "transform-origin: 50% 20%")
        self.assertContains(resp, "Zoom Photo")
        self.assertContains(resp, "LIGHTBOX MODAL")

    def test_theme_options_and_public_rendering(self):
        # Update invitation with romantic theme and Cormorant font
        self.invitation.theme_style = "romantic"
        self.invitation.font_family = "cormorant"
        self.invitation.theme_color = "#be185d"
        self.invitation.save()

        resp = self.client.get(f"/invite/{self.invitation.slug}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "theme-romantic")
        self.assertContains(resp, "--accent-color: #be185d")
        self.assertContains(resp, "'Cormorant Garamond', serif")

    def test_theme_options_form_submission(self):
        self.client.login(username="testuser", password="password123")
        response = self.client.post(
            f"/invitations/{self.invitation.slug}/edit/",
            {
                "title": "Midnight Gala",
                "slug": "emma-and-liam",
                "event_type": "corporate",
                "hosts_or_celebrants": "Emma & Liam",
                "event_date": "2027-10-10T19:00",
                "venue_summary": "Eiffel Tower Salon",
                "theme_style": "dark",
                "font_family": "cinzel",
                "theme_color": "#0f172a",
                "is_published": True,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.theme_style, "dark")
        self.assertEqual(self.invitation.font_family, "cinzel")
        self.assertEqual(self.invitation.theme_color, "#0f172a")

        # Public page should now have theme-dark and Cinzel
        resp = self.client.get(f"/invite/{self.invitation.slug}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "theme-dark")
        self.assertContains(resp, "'Cinzel', serif")

    def test_gallery_effect_default_and_choices(self):
        self.assertEqual(self.invitation.gallery_effect, "grid")
        for effect in ["slide", "carousel", "move", "fade", "grid"]:
            self.invitation.gallery_effect = effect
            self.invitation.save()
            self.invitation.refresh_from_db()
            self.assertEqual(self.invitation.gallery_effect, effect)

    def test_gallery_effect_update_view(self):
        self.client.login(username="testuser", password="password123")
        response = self.client.post(
            f"/invitations/{self.invitation.slug}/gallery/effect/",
            {"gallery_effect": "carousel"},
        )
        self.assertEqual(response.status_code, 302)
        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.gallery_effect, "carousel")

        # Test invalid effect is rejected
        response = self.client.post(
            f"/invitations/{self.invitation.slug}/gallery/effect/",
            {"gallery_effect": "unsupported_xyz"},
        )
        self.assertEqual(response.status_code, 302)
        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.gallery_effect, "carousel")

    def test_gallery_effect_form_edit(self):
        self.client.login(username="testuser", password="password123")
        response = self.client.post(
            f"/invitations/{self.invitation.slug}/edit/",
            {
                "title": "Emma & Liam Wedding",
                "slug": "emma-and-liam",
                "event_type": "wedding",
                "hosts_or_celebrants": "Emma & Liam",
                "event_date": "2027-10-10T19:00",
                "gallery_effect": "move",
                "is_published": True,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.gallery_effect, "move")

    def test_gallery_effect_public_page_render(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        import io
        from PIL import Image

        img = Image.new("RGB", (10, 10), color="blue")
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="JPEG")
        uploaded_image = SimpleUploadedFile("test_effect.jpg", img_bytes.getvalue(), content_type="image/jpeg")

        self.invitation.gallery_photos.create(image=uploaded_image, caption="Special Memory")
        self.invitation.gallery_effect = "move"
        self.invitation.save()

        resp = self.client.get(f"/invite/{self.invitation.slug}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "defaultGalleryEffect: 'move'")
        self.assertContains(resp, "animate-marquee-smooth")
        self.assertContains(resp, "Carousel")
        self.assertContains(resp, "Slide")
        self.assertContains(resp, "Move")
        self.assertContains(resp, "Fade")
        self.assertContains(resp, "Grid")

        # Switch to carousel
        self.invitation.gallery_effect = "carousel"
        self.invitation.save()
        resp2 = self.client.get(f"/invite/{self.invitation.slug}/")
        self.assertEqual(resp2.status_code, 200)
        self.assertContains(resp2, "defaultGalleryEffect: 'carousel'")




