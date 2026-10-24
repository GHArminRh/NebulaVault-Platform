from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from .forms import AccountPasswordResetForm, AccountSetPasswordForm

app_name = "accounts"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("verify/<str:uidb64>/<str:token>/", views.verify_email, name="verify_email"),
    path("verify/resend/", views.resend_verification, name="resend_verification"),
    path("profile/", views.profile, name="profile"),
    path("password/change/", views.password_change, name="password_change"),
    path(
        "password/reset/",
        auth_views.PasswordResetView.as_view(
            template_name="accounts/password_reset_form.html",
            email_template_name="registration/password_reset_email.html",
            subject_template_name="registration/password_reset_subject.txt",
            form_class=AccountPasswordResetForm,
            success_url="/accounts/password/reset/done/",
        ),
        name="password_reset",
    ),
    path(
        "password/reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="accounts/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "password/reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="accounts/password_reset_confirm.html",
            form_class=AccountSetPasswordForm,
            success_url="/accounts/password/reset/complete/",
        ),
        name="password_reset_confirm",
    ),
    path(
        "password/reset/complete/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="accounts/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
]
