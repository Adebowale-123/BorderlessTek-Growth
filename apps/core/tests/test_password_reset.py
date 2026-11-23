from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

LOCAL = {"DEBUG": True, "EMAIL_BACKEND": "django.core.mail.backends.console.EmailBackend"}
PROD = {"DEBUG": False, "EMAIL_BACKEND": "django.core.mail.backends.locmem.EmailBackend"}


class PasswordResetTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("admin", "boss@example.com", "old-password-123")

    def test_login_page_links_to_reset_and_reset_page_is_public(self):
        self.assertContains(self.client.get(reverse("login")), reverse("password_reset"))
        self.assertEqual(self.client.get(reverse("password_reset")).status_code, 200)

    @override_settings(**LOCAL)
    def test_local_mode_shows_link_by_username_and_link_resets_password(self):
        response = self.client.post(reverse("password_reset"), {"email": "ADMIN"}, follow=True)
        links = response.context["links"]
        self.assertEqual([u for u, _ in links], ["admin"])

        page = self.client.get(links[0][1], follow=True)  # Django swaps the token into the session
        self.assertTrue(page.context["validlink"])
        done = self.client.post(page.redirect_chain[-1][0],
                                {"new_password1": "Brand-new-pass-77", "new_password2": "Brand-new-pass-77"},
                                follow=True)
        self.assertContains(done, "Password changed")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Brand-new-pass-77"))

    @override_settings(**LOCAL)
    def test_local_mode_unknown_user(self):
        response = self.client.post(reverse("password_reset"), {"email": "nobody"}, follow=True)
        self.assertContains(response, "No account matches")

    @override_settings(**PROD, ALLOWED_HOSTS=["testserver"])
    def test_production_emails_link_and_never_shows_it(self):
        response = self.client.post(reverse("password_reset"), {"email": "admin"}, follow=True)
        self.assertContains(response, "Check your email")
        self.assertNotContains(response, "/password-reset/MQ")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["boss@example.com"])
        self.assertIn("/password-reset/", mail.outbox[0].body)

    @override_settings(**PROD, ALLOWED_HOSTS=["testserver"])
    def test_production_unknown_user_gives_same_answer(self):
        response = self.client.post(reverse("password_reset"), {"email": "nobody"}, follow=True)
        self.assertContains(response, "Check your email")
        self.assertEqual(len(mail.outbox), 0)
