from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from invitations.models import Guest, Invitation, Schedule, Wish

User = get_user_model()


class Command(BaseCommand):
    help = "Seed demo invitations with schedules, guests, and wishes"

    def handle(self, *args, **options):
        # Create or retrieve demo user
        user, created = User.objects.get_or_create(
            username="demo",
            defaults={"email": "demo@invito.app", "is_staff": True},
        )
        if created:
            user.set_password("demo12345")
            user.save()
            self.stdout.write(self.style.SUCCESS("Created demo user: demo / demo12345"))

        # Event 1: Wedding
        wedding_date = timezone.now() + timedelta(days=28)
        invitation, created = Invitation.objects.update_or_create(
            slug="sarah-and-alex",
            defaults={
                "user": user,
                "title": "The Wedding Celebration of Sarah & Alex",
                "event_type": "wedding",
                "hosts_or_celebrants": "Sarah Jenkins & Alex Rivera",
                "event_date": wedding_date.replace(hour=16, minute=0, second=0),
                "venue_summary": "The Glass House, Uluwatu, Bali",
                "cover_image_url": "https://images.unsplash.com/photo-1519741497674-611481863552?auto=format&fit=crop&w=1200&q=85",
                "audio_url": "https://cdn.pixabay.com/download/audio/2022/05/27/audio_1808fbf07a.mp3?filename=romantic-wedding-love-story-112191.mp3",
                "welcome_quote": "Two souls with but a single thought, two hearts that beat as one. Together with our families, we invite you to share our joy.",
                "theme_color": "#c28e46",
                "font_family": "cormorant",
                "gift_bank_name": "Bank of America / PayPal",
                "gift_account_number": "987-654-3210",
                "gift_account_name": "Sarah Jenkins & Alex Rivera",
                "gift_note": "Your blessings and love are the greatest gifts of all. If you wish to honor us with a digital token of appreciation, our registry is below.",
                "is_published": True,
            },
        )

        # Clear and reseed schedules
        invitation.schedules.all().delete()
        Schedule.objects.create(
            invitation=invitation,
            title="Sacred Holy Matrimony",
            start_time=wedding_date.replace(hour=15, minute=30, second=0),
            end_time=wedding_date.replace(hour=17, minute=0, second=0),
            venue_name="The Cliffside Chapel",
            address="Jl. Pantai Suluban No. 88, Uluwatu, Bali 80361",
            map_url="https://maps.google.com/?q=Uluwatu+Bali",
            dress_code="Formal Beach Chic / Earth Tones",
            order=1,
        )
        Schedule.objects.create(
            invitation=invitation,
            title="Cocktails & Grand Sunset Dinner",
            start_time=wedding_date.replace(hour=18, minute=0, second=0),
            end_time=wedding_date.replace(hour=23, minute=0, second=0),
            venue_name="The Glass House Garden",
            address="Jl. Pantai Suluban No. 88, Uluwatu, Bali 80361",
            map_url="https://maps.google.com/?q=Uluwatu+Bali",
            dress_code="Formal / Evening Elegance",
            order=2,
        )

        # Clear and reseed guests
        invitation.guests.all().delete()
        g1 = Guest.objects.create(
            invitation=invitation,
            name="John Doe & Partner",
            phone="+1 (555) 234-5678",
            email="john@example.com",
            max_pax=2,
            is_attending=True,
            actual_pax=2,
            notes="Vegetarian meals preferred.",
        )
        g2 = Guest.objects.create(
            invitation=invitation,
            name="Jessica Miller",
            phone="+1 (555) 987-6543",
            email="jessica@example.com",
            max_pax=1,
            is_attending=True,
            actual_pax=1,
        )
        g3 = Guest.objects.create(
            invitation=invitation,
            name="Marcus Holloway",
            phone="+1 (555) 345-6789",
            email="marcus@example.com",
            max_pax=2,
            is_attending=False,
            notes="Sending love from afar! Wish I could be there.",
        )

        # Clear and reseed wishes
        invitation.wishes.all().delete()
        Wish.objects.create(
            invitation=invitation,
            guest=g1,
            sender_name="John Doe",
            attendance_status="attending",
            message="Congratulations Sarah and Alex! So excited to witness your special day in Bali! Wishing you a lifetime of laughter and happiness.",
        )
        Wish.objects.create(
            invitation=invitation,
            guest=g2,
            sender_name="Jessica Miller",
            attendance_status="attending",
            message="You two are truly made for each other. Can't wait to dance the night away with you both!",
        )
        Wish.objects.create(
            invitation=invitation,
            guest=g3,
            sender_name="Marcus Holloway",
            attendance_status="declined",
            message="Heartiest congratulations on your union! May God shower endless blessings, harmony, and joy upon your new journey.",
        )

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded demo invitation: '{invitation.slug}'"))
