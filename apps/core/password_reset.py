"""Forgotten-password flow: ask for a username or email, then send a one-time reset link.

In production the link is emailed. When running locally with no email server configured (DEBUG and the
console email backend), the link is shown on screen instead, so a reset never needs the terminal.
"""

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth import views as auth_views
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.tokens import default_token_generator
from django.db.models import Q
from django.urls import reverse, reverse_lazy
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

SHOW_LINK_SESSION_KEY = "password_reset_links"


def show_link_on_screen():
    """True only for local development with no real email server."""
    return settings.DEBUG and settings.EMAIL_BACKEND.endswith("console.EmailBackend")


class UsernameOrEmailResetForm(PasswordResetForm):
    email = forms.CharField(
        label="Username or email",
        max_length=254,
        widget=forms.TextInput(attrs={"autocomplete": "username", "autofocus": True}),
    )

    def get_users(self, email):
        value = email.strip()
        users = get_user_model()._default_manager.filter(
            Q(username__iexact=value) | Q(email__iexact=value), is_active=True
        )
        return (u for u in users if u.has_usable_password())


class ForgotPasswordView(auth_views.PasswordResetView):
    form_class = UsernameOrEmailResetForm
    template_name = "registration/forgot_password.html"
    email_template_name = "registration/password_reset_email.txt"
    subject_template_name = "registration/password_reset_subject.txt"
    success_url = reverse_lazy("password_reset_done")

    def form_valid(self, form):
        self.request.session.pop(SHOW_LINK_SESSION_KEY, None)
        if show_link_on_screen():
            links = [
                (user.get_username(), self.request.build_absolute_uri(reverse(
                    "password_reset_confirm",
                    kwargs={"uidb64": urlsafe_base64_encode(force_bytes(user.pk)),
                            "token": default_token_generator.make_token(user)},
                )))
                for user in form.get_users(form.cleaned_data["email"])
            ]
            self.request.session[SHOW_LINK_SESSION_KEY] = links
        return super().form_valid(form)


class ForgotPasswordDoneView(auth_views.PasswordResetDoneView):
    template_name = "registration/forgot_password_done.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["local_mode"] = show_link_on_screen()
        context["links"] = self.request.session.pop(SHOW_LINK_SESSION_KEY, None) if context["local_mode"] else None
        return context


class ResetPasswordView(auth_views.PasswordResetConfirmView):
    template_name = "registration/reset_password.html"
    success_url = reverse_lazy("password_reset_complete")


class ResetPasswordCompleteView(auth_views.PasswordResetCompleteView):
    template_name = "registration/reset_password_complete.html"
