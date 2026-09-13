from django import forms
from .models import Invitation, Schedule, Guest, Wish, GalleryPhoto, normalize_gdrive_url


class InvitationForm(forms.ModelForm):
    cover_image_url = forms.CharField(
        required=False,
        widget=forms.URLInput(attrs={"class": "form-input", "placeholder": "https://... (or upload file above)"}),
    )
    audio_url = forms.CharField(
        required=False,
        widget=forms.URLInput(attrs={"class": "form-input", "placeholder": "https://.../song.mp3 (or upload file above)"}),
    )

    class Meta:
        model = Invitation
        fields = [
            "title",
            "slug",
            "event_type",
            "hosts_or_celebrants",
            "event_date",
            "venue_summary",
            "cover_image",
            "cover_image_url",
            "cover_focus_position",
            "cover_zoom_level",
            "audio_file",
            "audio_url",
            "welcome_quote",
            "theme_color",
            "font_family",
            "theme_style",
            "gallery_effect",
            "gift_bank_name",
            "gift_account_number",
            "gift_account_name",
            "gift_note",
            "is_published",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-input", "placeholder": "The Wedding of Sarah & Alex"}),
            "slug": forms.TextInput(attrs={"class": "form-input", "placeholder": "sarah-alex-wedding (leave empty to auto-generate)"}),
            "event_type": forms.Select(attrs={"class": "form-select"}),
            "hosts_or_celebrants": forms.TextInput(attrs={"class": "form-input", "placeholder": "Sarah Jenkins & Alex Rivera"}),
            "event_date": forms.DateTimeInput(attrs={"class": "form-input", "type": "datetime-local"}),
            "venue_summary": forms.TextInput(attrs={"class": "form-input", "placeholder": "The Glasshouse, Uluwatu, Bali"}),
            "cover_image": forms.ClearableFileInput(attrs={"class": "form-file-input", "accept": "image/*"}),
            "cover_focus_position": forms.TextInput(attrs={"class": "form-input", "placeholder": "e.g. center, top, 50% 20%"}),
            "cover_zoom_level": forms.NumberInput(attrs={"class": "form-input", "min": 100, "max": 250, "step": 5}),
            "audio_file": forms.ClearableFileInput(attrs={"class": "form-file-input", "accept": "audio/mp3,audio/*"}),
            "welcome_quote": forms.Textarea(attrs={"class": "form-textarea", "rows": 3}),
            "theme_color": forms.TextInput(attrs={"class": "form-input", "type": "color"}),
            "font_family": forms.Select(attrs={"class": "form-select"}),
            "theme_style": forms.Select(attrs={"class": "form-select"}),
            "gallery_effect": forms.Select(attrs={"class": "form-select"}),
            "gift_bank_name": forms.TextInput(attrs={"class": "form-input", "placeholder": "e.g. Bank Central Asia / PayPal / Chase"}),
            "gift_account_number": forms.TextInput(attrs={"class": "form-input", "placeholder": "e.g. 1234567890"}),
            "gift_account_name": forms.TextInput(attrs={"class": "form-input", "placeholder": "e.g. Alex Rivera"}),
            "gift_note": forms.Textarea(attrs={"class": "form-textarea", "rows": 2}),
            "is_published": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }

    def clean_cover_image_url(self):
        url = (self.cleaned_data.get("cover_image_url") or "").strip()
        if not url:
            return ""
        # Auto-convert Google Drive links to direct image CDN links
        url = normalize_gdrive_url(url, media_type="image")
        if url.startswith("blob:") or url.startswith("/media/"):
            return ""
        if not url.startswith(("http://", "https://")):
            if self.cleaned_data.get("cover_image") or (self.instance and getattr(self.instance, "cover_image", None)):
                return ""
            raise forms.ValidationError("Enter a valid image URL starting with http:// or https://")
        return url

    def clean_audio_url(self):
        url = (self.cleaned_data.get("audio_url") or "").strip()
        if not url:
            return ""
        # Auto-convert Google Drive links to direct audio stream links
        url = normalize_gdrive_url(url, media_type="audio")
        if url.startswith("blob:") or url.startswith("/media/"):
            return ""
        if not url.startswith(("http://", "https://")):
            if self.cleaned_data.get("audio_file") or (self.instance and getattr(self.instance, "audio_file", None)):
                return ""
        return url

    def clean_theme_style(self):
        val = (self.cleaned_data.get("theme_style") or "").strip()
        return val or "classic"

    def clean_font_family(self):
        val = (self.cleaned_data.get("font_family") or "").strip()
        return val or "serif"

    def clean_theme_color(self):
        val = (self.cleaned_data.get("theme_color") or "").strip()
        return val or "#b45309"



class GalleryPhotoForm(forms.ModelForm):
    class Meta:
        model = GalleryPhoto
        fields = ["image", "caption"]
        widgets = {
            "image": forms.ClearableFileInput(attrs={"class": "form-file-input", "accept": "image/*", "required": "required"}),
            "caption": forms.TextInput(attrs={"class": "form-input", "placeholder": "e.g. Pre-wedding moment, Reception dance, etc."}),
        }


class ScheduleForm(forms.ModelForm):
    class Meta:
        model = Schedule
        fields = [
            "title",
            "start_time",
            "end_time",
            "venue_name",
            "address",
            "map_url",
            "dress_code",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-input", "placeholder": "Ceremony / Reception / Party"}),
            "start_time": forms.DateTimeInput(attrs={"class": "form-input", "type": "datetime-local"}),
            "end_time": forms.DateTimeInput(attrs={"class": "form-input", "type": "datetime-local"}),
            "venue_name": forms.TextInput(attrs={"class": "form-input", "placeholder": "Chapel of Love"}),
            "address": forms.Textarea(attrs={"class": "form-textarea", "rows": 2, "placeholder": "Full venue address"}),
            "map_url": forms.URLInput(attrs={"class": "form-input", "placeholder": "https://maps.google.com/..."}),
            "dress_code": forms.TextInput(attrs={"class": "form-input", "placeholder": "e.g. Formal, Neutral or Pastel shades"}),
        }


class GuestForm(forms.ModelForm):
    class Meta:
        model = Guest
        fields = ["name", "phone", "email", "max_pax"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-input", "placeholder": "Full name or Family name"}),
            "phone": forms.TextInput(attrs={"class": "form-input", "placeholder": "+1 234 567 8900"}),
            "email": forms.EmailInput(attrs={"class": "form-input", "placeholder": "guest@example.com"}),
            "max_pax": forms.NumberInput(attrs={"class": "form-input", "min": 1, "value": 1}),
        }


class PublicRSVPForm(forms.Form):
    guest_name = forms.CharField(
        max_length=120,
        widget=forms.TextInput(attrs={"class": "rsvp-input", "placeholder": "Your Name"}),
    )
    is_attending = forms.ChoiceField(
        choices=[("yes", "Yes, I will attend with pleasure"), ("no", "Sorry, I cannot attend")],
        widget=forms.RadioSelect(attrs={"class": "rsvp-radio"}),
    )
    actual_pax = forms.IntegerField(
        min_value=1,
        max_value=10,
        initial=1,
        widget=forms.NumberInput(attrs={"class": "rsvp-input", "min": 1, "max": 10}),
        required=False,
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "rsvp-input", "rows": 2, "placeholder": "Dietary restrictions or notes (optional)"}),
    )


class PublicWishForm(forms.ModelForm):
    class Meta:
        model = Wish
        fields = ["sender_name", "attendance_status", "message"]
        widgets = {
            "sender_name": forms.TextInput(attrs={"class": "wish-input", "placeholder": "Your Name"}),
            "attendance_status": forms.Select(attrs={"class": "wish-select"}),
            "message": forms.Textarea(attrs={"class": "wish-textarea", "rows": 3, "placeholder": "Write your warm prayers, wishes, or greeting..."}),
        }
