from urllib.parse import quote
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import (
    GalleryPhotoForm,
    GuestForm,
    InvitationForm,
    PublicRSVPForm,
    PublicWishForm,
    ScheduleForm,
)
from .models import GalleryPhoto, Guest, Invitation, Schedule, Wish


def signup_view(request):
    """Register a new SaaS user account."""
    if request.user.is_authenticated:
        return redirect("invitations:dashboard")

    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome to Invito, {user.username}! Let's create your first invitation.")
            return redirect("invitations:dashboard")
    else:
        form = UserCreationForm()
    return render(request, "registration/signup.html", {"form": form})


@login_required
def dashboard_view(request):
    """Creator dashboard: list invitations with attendance statistics."""
    invitations = (
        Invitation.objects.filter(user=request.user)
        .annotate(
            total_guests=Count("guests", distinct=True),
            attending_guests=Count("guests", filter=Q(guests__is_attending=True), distinct=True),
            declined_guests=Count("guests", filter=Q(guests__is_attending=False), distinct=True),
            total_wishes=Count("wishes", distinct=True),
        )
        .order_by("-created_at")
    )
    return render(request, "invitations/dashboard.html", {"invitations": invitations})


@login_required
def invitation_create_view(request):
    """Create a new invitation."""
    if request.method == "POST":
        form = InvitationForm(request.POST, request.FILES)
        if form.is_valid():
            invitation = form.save(commit=False)
            invitation.user = request.user
            invitation.save()
            messages.success(request, f"Invitation '{invitation.title}' created successfully!")
            return redirect("invitations:invitation_detail", slug=invitation.slug)
        else:
            err_details = "; ".join([f"{k}: {', '.join(v)}" for k, v in form.errors.items()])
            messages.error(request, f"Error creating invitation. Please check fields: {err_details}")
    else:
        # Default with a future event date
        initial_date = timezone.now() + timezone.timedelta(days=30)
        form = InvitationForm(initial={"event_date": initial_date.strftime("%Y-%m-%dT10:00")})

    return render(
        request,
        "invitations/invitation_form.html",
        {"form": form, "title": "Create Digital Invitation", "is_create": True},
    )


@login_required
def invitation_edit_view(request, slug):
    """Edit an existing invitation."""
    invitation = get_object_or_404(Invitation, slug=slug, user=request.user)
    if request.method == "POST":
        form = InvitationForm(request.POST, request.FILES, instance=invitation)
        if form.is_valid():
            invitation = form.save()
            messages.success(request, f"Invitation '{invitation.title}' updated successfully!")
            return redirect("invitations:invitation_detail", slug=invitation.slug)
        else:
            err_details = "; ".join([f"{k}: {', '.join(v)}" for k, v in form.errors.items()])
            messages.error(request, f"Error saving invitation. Please check fields: {err_details}")
    else:
        form = InvitationForm(instance=invitation)

    return render(
        request,
        "invitations/invitation_form.html",
        {"form": form, "invitation": invitation, "title": f"Edit {invitation.title}", "is_create": False},
    )


@login_required
def invitation_detail_view(request, slug):
    """Creator overview for an invitation: schedules, gallery, guests, wishes, and shareable links."""
    invitation = get_object_or_404(Invitation, slug=slug, user=request.user)
    schedules = invitation.schedules.all()
    gallery_photos = invitation.get_all_gallery_photos()
    db_gallery_photos = invitation.gallery_photos.all()
    guests = invitation.guests.all()
    wishes = invitation.wishes.all()

    # Calculate stats
    attending_count = guests.filter(is_attending=True).count()
    total_attending_pax = sum(g.actual_pax for g in guests.filter(is_attending=True))
    declined_count = guests.filter(is_attending=False).count()
    pending_count = guests.filter(is_attending__isnull=True).count()

    schedule_form = ScheduleForm()
    gallery_form = GalleryPhotoForm()
    guest_form = GuestForm()

    # Generate sample share link
    base_url = request.build_absolute_uri(f"/invite/{invitation.slug}/")

    context = {
        "invitation": invitation,
        "schedules": schedules,
        "gallery_photos": gallery_photos,
        "db_gallery_photos": db_gallery_photos,
        "guests": guests,
        "wishes": wishes,
        "attending_count": attending_count,
        "total_attending_pax": total_attending_pax,
        "declined_count": declined_count,
        "pending_count": pending_count,
        "schedule_form": schedule_form,
        "gallery_form": gallery_form,
        "guest_form": guest_form,
        "base_url": base_url,
    }
    return render(request, "invitations/invitation_detail.html", context)


@login_required
@require_POST
def schedule_add_view(request, slug):
    """Add a schedule block to an invitation."""
    invitation = get_object_or_404(Invitation, slug=slug, user=request.user)
    form = ScheduleForm(request.POST)
    if form.is_valid():
        schedule = form.save(commit=False)
        schedule.invitation = invitation
        schedule.save()
        messages.success(request, f"Event agenda item '{schedule.title}' added.")
    else:
        err_details = "; ".join([f"{k}: {', '.join(v)}" for k, v in form.errors.items()])
        messages.error(request, f"Error adding schedule item: {err_details}")
    return redirect("invitations:invitation_detail", slug=invitation.slug)


@login_required
@require_POST
def schedule_delete_view(request, slug, schedule_id):
    """Delete a schedule item."""
    invitation = get_object_or_404(Invitation, slug=slug, user=request.user)
    schedule = get_object_or_404(Schedule, id=schedule_id, invitation=invitation)
    schedule.delete()
    messages.success(request, "Schedule item removed.")
    return redirect("invitations:invitation_detail", slug=invitation.slug)


@login_required
@require_POST
def gallery_photo_add_view(request, slug):
    """Upload a photo to an invitation's event gallery."""
    invitation = get_object_or_404(Invitation, slug=slug, user=request.user)
    form = GalleryPhotoForm(request.POST, request.FILES)
    if form.is_valid():
        photo = form.save(commit=False)
        photo.invitation = invitation
        photo.save()
        messages.success(request, "Photo uploaded to gallery successfully!")
    else:
        err_details = "; ".join([f"{k}: {', '.join(v)}" for k, v in form.errors.items()])
        messages.error(request, f"Error uploading photo: {err_details}")
    return redirect("invitations:invitation_detail", slug=invitation.slug)


@login_required
@require_POST
def gallery_photo_delete_view(request, slug, photo_id):
    """Delete a photo from the gallery."""
    invitation = get_object_or_404(Invitation, slug=slug, user=request.user)
    photo = get_object_or_404(GalleryPhoto, id=photo_id, invitation=invitation)
    if photo.image:
        photo.image.delete(save=False)
    photo.delete()
    messages.success(request, "Photo removed from gallery.")
    return redirect("invitations:invitation_detail", slug=invitation.slug)


@login_required
@require_POST
def gallery_effect_update_view(request, slug):
    """Update the gallery display & animation effect for an invitation."""
    invitation = get_object_or_404(Invitation, slug=slug, user=request.user)
    effect = request.POST.get("gallery_effect", "grid").strip()
    valid_effects = [choice[0] for choice in Invitation.GALLERY_EFFECT_CHOICES]
    if effect in valid_effects:
        invitation.gallery_effect = effect
        invitation.save(update_fields=["gallery_effect"])
        messages.success(request, f"Gallery effect updated to '{invitation.get_gallery_effect_display()}'.")
    else:
        messages.error(request, "Invalid gallery effect selected.")
    return redirect("invitations:invitation_detail", slug=invitation.slug)


@login_required
@require_POST
def gallery_folder_sync_view(request, slug):
    """Sync all photos from the Google Drive folder into GalleryPhoto records."""
    from .gdrive import fetch_photos_from_gdrive_folder

    invitation = get_object_or_404(Invitation, slug=slug, user=request.user)
    folder_url = request.POST.get("gallery_folder_url", "").strip() or invitation.gallery_folder_url
    if not folder_url:
        messages.error(request, "Please provide a Google Drive folder URL.")
        return redirect("invitations:invitation_detail", slug=invitation.slug)

    if folder_url != invitation.gallery_folder_url:
        invitation.gallery_folder_url = folder_url
        invitation.save(update_fields=["gallery_folder_url"])

    photos = fetch_photos_from_gdrive_folder(folder_url)
    if not photos:
        messages.warning(
            request,
            "Could not discover photos in this Google Drive folder. "
            "Please ensure the folder's General Access is set to 'Anyone with the link can view'."
        )
        return redirect("invitations:invitation_detail", slug=invitation.slug)

    created_count = 0
    existing_urls = set(invitation.gallery_photos.values_list("image_url", flat=True))
    for item in photos:
        url = item.get("url")
        if url and url not in existing_urls:
            GalleryPhoto.objects.create(
                invitation=invitation,
                image_url=url,
                caption=item.get("caption", ""),
            )
            created_count += 1

    messages.success(request, f"Successfully imported {created_count} photos from Google Drive folder!")
    return redirect("invitations:invitation_detail", slug=invitation.slug)


@login_required
@require_POST
def guest_add_view(request, slug):
    """Add a guest to the guest list and generate a personalized invitation URL."""
    invitation = get_object_or_404(Invitation, slug=slug, user=request.user)
    form = GuestForm(request.POST)
    if form.is_valid():
        guest = form.save(commit=False)
        guest.invitation = invitation
        guest.save()
        messages.success(request, f"Guest '{guest.name}' added with custom link.")
    else:
        err_details = "; ".join([f"{k}: {', '.join(v)}" for k, v in form.errors.items()])
        messages.error(request, f"Error adding guest: {err_details}")
    return redirect("invitations:invitation_detail", slug=invitation.slug)


@login_required
@require_POST
def guest_delete_view(request, slug, guest_id):
    """Delete a guest."""
    invitation = get_object_or_404(Invitation, slug=slug, user=request.user)
    guest = get_object_or_404(Guest, id=guest_id, invitation=invitation)
    guest.delete()
    messages.success(request, "Guest removed.")
    return redirect("invitations:invitation_detail", slug=invitation.slug)


@login_required
@require_POST
def invitation_delete_view(request, slug):
    """Delete an entire invitation."""
    invitation = get_object_or_404(Invitation, slug=slug, user=request.user)
    invitation.delete()
    messages.success(request, f"Invitation '{invitation.title}' has been deleted.")
    return redirect("invitations:dashboard")


# =======================================================================
# PUBLIC MOBILE-FIRST INVITATION VIEWS
# =======================================================================


def public_invitation_view(request, slug):
    """The mobile-first public invitation page with OpenGraph & rich interactive elements."""
    invitation = get_object_or_404(Invitation, slug=slug)

    # Check if guest was specified in URL query
    # e.g. /invite/slug/?to=John+Doe or /invite/slug/?guest=john-doe
    guest_name = request.GET.get("to", "").strip()
    guest_slug = request.GET.get("guest", "").strip()
    guest_obj = None

    if guest_slug:
        guest_obj = invitation.guests.filter(slug=guest_slug).first()
        if guest_obj:
            guest_name = guest_obj.name
    elif guest_name:
        guest_obj = invitation.guests.filter(name__iexact=guest_name).first()

    schedules = invitation.schedules.all()
    gallery_photos = invitation.get_all_gallery_photos()
    wishes = invitation.wishes.all()[:50]

    # Prepopulate RSVP form
    initial_rsvp = {}
    if guest_obj:
        initial_rsvp["guest_name"] = guest_obj.name
        if guest_obj.is_attending is not None:
            initial_rsvp["is_attending"] = "yes" if guest_obj.is_attending else "no"
        initial_rsvp["actual_pax"] = guest_obj.actual_pax
        initial_rsvp["notes"] = guest_obj.notes
    elif guest_name:
        initial_rsvp["guest_name"] = guest_name

    rsvp_form = PublicRSVPForm(initial=initial_rsvp)
    wish_form = PublicWishForm(initial={"sender_name": guest_name} if guest_name else None)

    # Prepare OpenGraph metadata
    current_url = request.build_absolute_uri()
    og_description = (
        f"You are cordially invited to {invitation.title}. "
        f"Event Date: {invitation.event_date.strftime('%A, %d %B %Y')} at {invitation.venue_summary or 'See details inside'}."
    )

    context = {
        "invitation": invitation,
        "schedules": schedules,
        "gallery_photos": gallery_photos,
        "wishes": wishes,
        "guest_name": guest_name,
        "guest_obj": guest_obj,
        "rsvp_form": rsvp_form,
        "wish_form": wish_form,
        "current_url": current_url,
        "og_description": og_description,
    }
    return render(request, "invitations/public_invitation.html", context)


@require_POST
def submit_rsvp_view(request, slug):
    """Handle public RSVP submission (supports AJAX and standard POST)."""
    invitation = get_object_or_404(Invitation, slug=slug)
    form = PublicRSVPForm(request.POST)

    if form.is_valid():
        guest_name = form.cleaned_data["guest_name"].strip()
        is_attending = form.cleaned_data["is_attending"] == "yes"
        actual_pax = form.cleaned_data.get("actual_pax") or 1
        notes = form.cleaned_data.get("notes", "").strip()

        # Check if guest exists or create new guest record
        guest, _ = Guest.objects.get_or_create(
            invitation=invitation,
            name__iexact=guest_name,
            defaults={"name": guest_name, "max_pax": actual_pax},
        )
        guest.is_attending = is_attending
        guest.actual_pax = actual_pax
        guest.notes = notes
        guest.save()

        if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.GET.get("format") == "json":
            return JsonResponse({
                "success": True,
                "message": "Thank you! Your RSVP response has been recorded.",
                "attending": is_attending,
                "pax": actual_pax,
            })

        messages.success(request, "Thank you! Your RSVP response has been recorded.")
        return redirect(f"/invite/{invitation.slug}/?to={quote(guest_name)}#rsvp")

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"success": False, "errors": form.errors}, status=400)

    messages.error(request, "Please complete the RSVP form properly.")
    return redirect(f"/invite/{invitation.slug}/#rsvp")


@require_POST
def submit_wish_view(request, slug):
    """Handle public wishes/guestbook submission (supports AJAX and standard POST)."""
    invitation = get_object_or_404(Invitation, slug=slug)
    form = PublicWishForm(request.POST)

    if form.is_valid():
        wish = form.save(commit=False)
        wish.invitation = invitation

        # Attempt to link with known guest
        guest = invitation.guests.filter(name__iexact=wish.sender_name).first()
        if guest:
            wish.guest = guest

        wish.save()

        if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.GET.get("format") == "json":
            return JsonResponse({
                "success": True,
                "message": "Thank you for your warm wish!",
                "wish": {
                    "id": wish.id,
                    "sender_name": wish.sender_name,
                    "status": wish.get_attendance_status_display(),
                    "message": wish.message,
                    "created_at": wish.created_at.strftime("%b %d, %Y, %I:%M %p"),
                },
            })

        messages.success(request, "Thank you for sending your warm wishes!")
        return redirect(f"/invite/{invitation.slug}/#wishes")

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"success": False, "errors": form.errors}, status=400)

    messages.error(request, "Please fill in all required fields.")
    return redirect(f"/invite/{invitation.slug}/#wishes")
