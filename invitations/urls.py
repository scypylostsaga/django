from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "invitations"

urlpatterns = [
    # Auth
    path("signup/", views.signup_view, name="signup"),
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    # SaaS Creator Dashboard
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("invitations/create/", views.invitation_create_view, name="invitation_create"),
    path("invitations/<slug:slug>/", views.invitation_detail_view, name="invitation_detail"),
    path("invitations/<slug:slug>/edit/", views.invitation_edit_view, name="invitation_edit"),
    path("invitations/<slug:slug>/delete/", views.invitation_delete_view, name="invitation_delete"),

    # Schedule, Gallery & Guest Management
    path("invitations/<slug:slug>/schedules/add/", views.schedule_add_view, name="schedule_add"),
    path("invitations/<slug:slug>/schedules/<int:schedule_id>/delete/", views.schedule_delete_view, name="schedule_delete"),
    path("invitations/<slug:slug>/gallery/add/", views.gallery_photo_add_view, name="gallery_photo_add"),
    path("invitations/<slug:slug>/gallery/<int:photo_id>/delete/", views.gallery_photo_delete_view, name="gallery_photo_delete"),
    path("invitations/<slug:slug>/gallery/effect/", views.gallery_effect_update_view, name="gallery_effect_update"),
    path("invitations/<slug:slug>/guests/add/", views.guest_add_view, name="guest_add"),
    path("invitations/<slug:slug>/guests/<int:guest_id>/delete/", views.guest_delete_view, name="guest_delete"),

    # Public Mobile-First Invitation & Interactions
    path("invite/<slug:slug>/", views.public_invitation_view, name="public_invitation"),
    path("invite/<slug:slug>/rsvp/", views.submit_rsvp_view, name="submit_rsvp"),
    path("invite/<slug:slug>/wishes/", views.submit_wish_view, name="submit_wish"),
]
