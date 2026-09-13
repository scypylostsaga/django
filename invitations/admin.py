from django.contrib import admin
from .models import Invitation, Schedule, Guest, Wish, GalleryPhoto


class GalleryPhotoInline(admin.TabularInline):
    model = GalleryPhoto
    extra = 1


class ScheduleInline(admin.TabularInline):
    model = Schedule
    extra = 1


class GuestInline(admin.TabularInline):
    model = Guest
    extra = 1


class WishInline(admin.TabularInline):
    model = Wish
    extra = 0
    readonly_fields = ["created_at"]


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ["title", "user", "event_type", "gallery_effect", "event_date", "is_published", "created_at"]
    list_filter = ["event_type", "gallery_effect", "is_published", "created_at"]
    search_fields = ["title", "hosts_or_celebrants", "slug"]
    prepopulated_fields = {"slug": ("title",)}
    inlines = [ScheduleInline, GalleryPhotoInline, GuestInline, WishInline]


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ["title", "invitation", "start_time", "venue_name", "order"]
    list_filter = ["invitation"]
    search_fields = ["title", "venue_name"]


@admin.register(Guest)
class GuestAdmin(admin.ModelAdmin):
    list_display = ["name", "invitation", "slug", "phone", "is_attending", "actual_pax", "created_at"]
    list_filter = ["is_attending", "invitation"]
    search_fields = ["name", "phone", "email", "slug"]


@admin.register(Wish)
class WishAdmin(admin.ModelAdmin):
    list_display = ["sender_name", "invitation", "attendance_status", "created_at"]
    list_filter = ["attendance_status", "invitation", "created_at"]
    search_fields = ["sender_name", "message"]
