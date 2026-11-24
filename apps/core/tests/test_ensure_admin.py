from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from unittest import mock

ENV = {"ADMIN_USERNAME": "boss", "ADMIN_PASSWORD": "Env-pass-123", "ADMIN_EMAIL": "boss@example.com"}


def run(**extra):
    with mock.patch.dict("os.environ", {**ENV, **extra}):
        call_command("ensure_admin", stdout=mock.MagicMock())


class EnsureAdminTests(TestCase):
    def test_creates_admin_with_email(self):
        run()
        user = User.objects.get(username="boss")
        self.assertTrue(user.is_superuser and user.check_password("Env-pass-123"))
        self.assertEqual(user.email, "boss@example.com")

    def test_existing_admin_gets_missing_email_but_keeps_password(self):
        User.objects.create_superuser("boss", "", "Old-pass-123")
        run()
        user = User.objects.get(username="boss")
        self.assertEqual(user.email, "boss@example.com")
        self.assertTrue(user.check_password("Old-pass-123"))

    def test_existing_email_is_not_overwritten(self):
        User.objects.create_superuser("boss", "kept@example.com", "Old-pass-123")
        run()
        self.assertEqual(User.objects.get(username="boss").email, "kept@example.com")

    def test_reset_flag_sets_password_from_env(self):
        User.objects.create_superuser("boss", "", "Old-pass-123")
        run(ADMIN_RESET_PASSWORD="true")
        self.assertTrue(User.objects.get(username="boss").check_password("Env-pass-123"))
