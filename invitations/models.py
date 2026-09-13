import re
from urllib.parse import quote_plus
from django.conf import settings
from django.db import models
from django.utils.text import slugify


def normalize_gdrive_url(url: str, media_type: str = "image") -> str:
    """
    Transforms standard Google Drive file/view sharing links into direct CDN stream links.
    e.g. https://drive.google.com/file/d/<FILE_ID>/view?usp=sharing
    -> For images: https://lh3.googleusercontent.com/d/<FILE_ID>
    -> For audio:  https://docs.google.com/uc?export=download&id=<FILE_ID>
    """
    if not url:
        return ""
    url = url.strip()
    if ("drive.google.com" in url or "docs.google.com" in url) and ("file/d/" in url or "id=" in url):
        match = re.search(r"(?:file/d/|id=)([a-zA-Z0-9_-]{20,})", url)
        if match:
            file_id = match.group(1)
            if media_type == "image":
                return f"https://lh3.googleusercontent.com/d/{file_id}"
            elif media_type == "audio":
                return f"https://docs.google.com/uc?export=download&id={file_id}"
    return url


class Invitation(models.Model):
    EVENT_TYPES = [
        ("wedding", "Wedding"),
        ("birthday", "Birthday Celebration"),
        ("anniversary", "Anniversary"),
        ("baby_shower", "Baby Shower"),
        ("corporate", "Corporate Event / Gathering"),
        ("graduation", "Graduation"),
        ("general", "Celebration / Party"),
    ]

    FONT_CHOICES = [
        ("serif", "Classic Serif (Playfair Display)"),
        ("cormorant", "Timeless Romance (Cormorant Garamond)"),
        ("cinzel", "Regal Royal (Cinzel)"),
        ("greatvibes", "Romantic Calligraphy (Great Vibes)"),
        ("lora", "Poetic Literature (Lora)"),
        ("sans", "Modern Clean (Plus Jakarta Sans)"),
        ("montserrat", "Contemporary Editorial (Montserrat)"),
    ]

    THEME_STYLE_CHOICES = [
        ("classic", "Classic Ivory & Stone (Warm & Timeless)"),
        ("dark", "Midnight Luxe / Black Tie (Dramatic & Sleek)"),
        ("minimal", "Pure Minimal White (Crisp & Clean)"),
        ("romantic", "Blush Petal (Soft & Romantic)"),
        ("botanical", "Botanical Garden (Lush & Natural)"),
    ]

    GALLERY_EFFECT_CHOICES = [
        ("grid", "Classic Grid (Masonry)"),
        ("slide", "Smooth Slide (Horizontal Scroll)"),
        ("carousel", "Interactive Carousel (Slideshow)"),
        ("move", "Continuous Move (Auto Marquee)"),
        ("fade", "Cinematic Crossfade Deck"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="invitations",
    )
    title = models.CharField(max_length=200, help_text="e.g. The Wedding of Sarah & Alex")
    slug = models.SlugField(max_length=150, unique=True, help_text="URL slug for the invitation")
    event_type = models.CharField(max_length=30, choices=EVENT_TYPES, default="wedding")
    hosts_or_celebrants = models.CharField(
        max_length=255,
        help_text="Couple names, birthday person, or host organization (e.g. Sarah & Alex)",
    )
    event_date = models.DateTimeField(help_text="Main date and time of the event")
    venue_summary = models.CharField(
        max_length=255,
        blank=True,
        help_text="Short venue & city name (e.g. The Glasshouse, Bali)",
    )
    cover_image = models.ImageField(
        upload_to="invitations/covers/",
        blank=True,
        null=True,
        help_text="Upload custom cover photo (PNG/JPG)",
    )
    cover_image_url = models.URLField(
        blank=True,
        default="https://images.unsplash.com/photo-1519741497674-611481863552?auto=format&fit=crop&w=1200&q=80",
        help_text="Direct image URL for cover banner & OpenGraph preview (used if no file uploaded)",
    )
    cover_focus_position = models.CharField(
        max_length=50,
        default="center",
        blank=True,
        help_text="Focal point / ROI for cover photo (e.g. 'center', 'top', '50% 20%')",
    )
    cover_zoom_level = models.PositiveIntegerField(
        default=100,
        blank=True,
        help_text="Cover photo zoom percentage (100 = 1.0x, 150 = 1.5x, 200 = 2.0x)",
    )
    audio_file = models.FileField(
        upload_to="invitations/audio/",
        blank=True,
        null=True,
        help_text="Upload custom background song (MP3)",
    )
    audio_url = models.URLField(
        blank=True,
        help_text="Optional direct MP3 URL for background music (used if no file uploaded)",
    )
    welcome_quote = models.TextField(
        blank=True,
        default="Together with our families, we warmly invite you to celebrate this special day with us.",
    )
    theme_color = models.CharField(
        max_length=30,
        default="#b45309",
        blank=True,
        help_text="Accent color hex code (e.g. #b45309, #4f46e5, #be185d)",
    )
    font_family = models.CharField(
        max_length=30,
        choices=FONT_CHOICES,
        default="serif",
        blank=True,
    )
    theme_style = models.CharField(
        max_length=30,
        choices=THEME_STYLE_CHOICES,
        default="classic",
        blank=True,
        help_text="Visual background and presentation theme",
    )
    gallery_effect = models.CharField(
        max_length=30,
        choices=GALLERY_EFFECT_CHOICES,
        default="grid",
        blank=True,
        help_text="Visual layout and animation effect for the photo gallery",
    )
    # Digital Envelope / Gift info
    gift_bank_name = models.CharField(max_length=100, blank=True, help_text="Bank or digital wallet name")
    gift_account_number = models.CharField(max_length=100, blank=True, help_text="Account/Phone number")
    gift_account_name = models.CharField(max_length=150, blank=True, help_text="Account holder name")
    gift_note = models.TextField(
        blank=True,
        default="Your presence and prayers mean the world to us. For those who asked about gifts, a digital envelope is available below.",
    )

    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.get_event_type_display()})"

    @property
    def get_cover_image_url(self):
        if self.cover_image:
            return self.cover_image.url
        raw = self.cover_image_url or ""
        return normalize_gdrive_url(raw, media_type="image")

    @property
    def cover_zoom_scale(self):
        val = self.cover_zoom_level or 100
        return round(max(100, min(val, 250)) / 100.0, 2)

    @property
    def get_audio_url(self):
        if self.audio_file:
            return self.audio_file.url
        raw = self.audio_url or ""
        return normalize_gdrive_url(raw, media_type="audio")

    def save(self, *args, **kwargs):
        if self.cover_image_url:
            self.cover_image_url = normalize_gdrive_url(self.cover_image_url, media_type="image")
        if self.audio_url:
            self.audio_url = normalize_gdrive_url(self.audio_url, media_type="audio")
        if not self.slug:
            base_slug = slugify(self.title) or "invitation"
            slug = base_slug
            counter = 1
            while Invitation.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)


class Schedule(models.Model):
    invitation = models.ForeignKey(
        Invitation,
        on_delete=models.CASCADE,
        related_name="schedules",
    )
    title = models.CharField(max_length=150, help_text="e.g. Holy Matrimony, Reception, Dinner Party")
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(blank=True, null=True)
    venue_name = models.CharField(max_length=200)
    address = models.TextField(blank=True)
    map_url = models.URLField(max_length=500, blank=True, help_text="Google Maps direction link")
    dress_code = models.CharField(max_length=150, blank=True, help_text="e.g. Formal, Pastel, Smart Casual")
    order = models.PositiveIntegerField(default=0, blank=True)

    class Meta:
        ordering = ["order", "start_time"]

    def __str__(self):
        return f"{self.title} - {self.invitation.title}"

    def save(self, *args, **kwargs):
        if not self.map_url and (self.venue_name or self.address):
            location_query = f"{self.venue_name} {self.address}".strip()
            self.map_url = f"https://www.google.com/maps/search/?api=1&query={quote_plus(location_query)}"
        super().save(*args, **kwargs)


class Guest(models.Model):
    invitation = models.ForeignKey(
        Invitation,
        on_delete=models.CASCADE,
        related_name="guests",
    )
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=160, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    max_pax = models.PositiveIntegerField(default=2, help_text="Max guest allocation")
    is_attending = models.BooleanField(
        null=True,
        blank=True,
        help_text="Null=Pending, True=Attending, False=Declined",
    )
    actual_pax = models.PositiveIntegerField(default=1)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        unique_together = ("invitation", "slug")

    def __str__(self):
        return f"{self.name} - {self.invitation.title}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name) or "guest"
            slug = base
            counter = 1
            while Guest.objects.filter(invitation=self.invitation, slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def rsvp_badge(self):
        if self.is_attending is True:
            return "Attending"
        elif self.is_attending is False:
            return "Declined"
        return "Awaiting Response"


class Wish(models.Model):
    ATTENDANCE_CHOICES = [
        ("attending", "Attending"),
        ("maybe", "Maybe"),
        ("declined", "Cannot Attend"),
    ]

    invitation = models.ForeignKey(
        Invitation,
        on_delete=models.CASCADE,
        related_name="wishes",
    )
    guest = models.ForeignKey(
        Guest,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="wishes",
    )
    sender_name = models.CharField(max_length=120)
    attendance_status = models.CharField(
        max_length=20,
        choices=ATTENDANCE_CHOICES,
        default="attending",
    )
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Wish from {self.sender_name} on {self.invitation.title}"


class GalleryPhoto(models.Model):
    invitation = models.ForeignKey(
        Invitation,
        on_delete=models.CASCADE,
        related_name="gallery_photos",
    )
    image = models.ImageField(upload_to="invitations/gallery/")
    caption = models.CharField(max_length=150, blank=True, help_text="Optional photo caption")
    order = models.PositiveIntegerField(default=0, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "-created_at"]

    def __str__(self):
        return f"Photo for {self.invitation.title} ({self.caption or 'Untitled'})"
