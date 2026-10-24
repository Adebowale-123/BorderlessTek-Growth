from django.db import models


class SiteSettings(models.Model):
    """One row of settings, edited on the Settings page."""

    company_name = models.CharField(max_length=80, default="BorderlessTek")
    website_url = models.URLField(blank=True, help_text="Your website, e.g. https://borderlesstek.com")
    booking_url = models.URLField(blank=True, help_text="Where parents book the onboarding call (e.g. your Calendly link).")
    team_member_name = models.CharField(max_length=60, blank=True,
                                        help_text="First name used when signing replies, e.g. “Ada”.")
    min_score = models.PositiveSmallIntegerField(default=45, help_text="Show posts scoring at least this (0–100).")
    max_age_days = models.PositiveSmallIntegerField(default=14, help_text="Ignore posts older than this many days.")
    scan_every_hours = models.PositiveSmallIntegerField(default=3, help_text="How often to look for new posts.")
    telegram_bot_token = models.CharField(max_length=200, blank=True)
    telegram_chat_id = models.CharField(max_length=100, blank=True)
    digest_emails = models.TextField(blank=True, help_text="One email address per line for the daily summary.")
    digest_hour = models.PositiveSmallIntegerField(default=8, help_text="Hour (UK time) to send the daily summary.")
    last_scan_at = models.DateTimeField(null=True, blank=True, editable=False)
    last_digest_on = models.DateField(null=True, blank=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = verbose_name_plural = "Settings"

    def __str__(self):
        return "Settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def email_list(self):
        return [line.strip() for line in self.digest_emails.splitlines() if "@" in line]
