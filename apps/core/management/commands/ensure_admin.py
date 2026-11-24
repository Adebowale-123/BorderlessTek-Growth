import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


def env_true(key):
    return os.environ.get(key, "").strip().lower() in ("1", "true", "yes", "on")


class Command(BaseCommand):
    help = ("Create the first admin from ADMIN_USERNAME / ADMIN_PASSWORD if it doesn't exist (used on deploy). "
            "An existing admin gets ADMIN_EMAIL if it has no email yet, and its password is reset to "
            "ADMIN_PASSWORD only when ADMIN_RESET_PASSWORD=true.")

    def handle(self, *args, **options):
        username = os.environ.get("ADMIN_USERNAME", "").strip()
        password = os.environ.get("ADMIN_PASSWORD", "")
        email = os.environ.get("ADMIN_EMAIL", "").strip()
        if not username or not password:
            self.stdout.write("ADMIN_USERNAME / ADMIN_PASSWORD not set; skipping admin creation.")
            return
        User = get_user_model()
        user = User.objects.filter(username=username).first()
        if user is None:
            User.objects.create_superuser(username, email, password)
            self.stdout.write(self.style.SUCCESS(f"Created admin {username}."))
            return

        changed = []
        if email and not user.email:
            user.email = email
            changed.append("email")
        if env_true("ADMIN_RESET_PASSWORD"):
            user.set_password(password)
            user.is_active = user.is_staff = user.is_superuser = True
            changed.append("password")
        if changed:
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Admin {username} updated: {', '.join(changed)}."))
        else:
            self.stdout.write(f"Admin {username} already exists; leaving it unchanged.")
