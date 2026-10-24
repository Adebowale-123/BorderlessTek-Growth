from datetime import timedelta

from django.conf import settings
from django.db import models

# Days after the last contact to follow up, then stop (a polite final note is the third message).
FOLLOW_UP_DAYS = [2, 5, 10]


class LeadQuerySet(models.QuerySet):
    def open(self):
        return self.exclude(stage__in=[Lead.Stage.ENROLLED, Lead.Stage.LOST])

    def due(self, day):
        return self.open().filter(next_follow_up__isnull=False, next_follow_up__lte=day)


class Lead(models.Model):
    """A parent we're talking to, from first contact to enrolment."""

    class Stage(models.TextChoices):
        NEW = "new", "New"
        CONTACTED = "contacted", "Contacted"
        TALKING = "talking", "In conversation"
        CALL_BOOKED = "call_booked", "Call booked"
        ENROLLED = "enrolled", "Enrolled"
        LOST = "lost", "Not now"

    class Channel(models.TextChoices):
        REDDIT = "reddit", "Reddit"
        FACEBOOK = "facebook", "Facebook"
        INSTAGRAM = "instagram", "Instagram"
        WHATSAPP = "whatsapp", "WhatsApp"
        EMAIL = "email", "Email"
        WEBSITE = "website", "Website"
        REFERRAL = "referral", "Referral"
        FORUM = "forum", "Forum / other site"
        OTHER = "other", "Other"

    parent_name = models.CharField(max_length=120, help_text="Name or username, as they introduced themselves.")
    channel = models.CharField(max_length=12, choices=Channel.choices, default=Channel.REDDIT)
    profile_url = models.URLField(max_length=600, blank=True, help_text="Where to reach them (profile or thread).")
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True, help_text="WhatsApp / phone, with country code.")
    country = models.CharField(max_length=60, blank=True)
    child_age = models.PositiveSmallIntegerField(null=True, blank=True)
    interests = models.CharField(max_length=200, blank=True, help_text="e.g. coding, animation")
    consent = models.BooleanField(default=False, help_text="The parent agreed to be contacted by email/WhatsApp.")
    stage = models.CharField(max_length=12, choices=Stage.choices, default=Stage.NEW, db_index=True)
    call_at = models.DateTimeField(null=True, blank=True, help_text="Onboarding call time (when booked).")
    next_follow_up = models.DateField(null=True, blank=True, db_index=True)
    follow_ups_sent = models.PositiveSmallIntegerField(default=0)
    opportunity = models.ForeignKey("finder.Opportunity", null=True, blank=True, on_delete=models.SET_NULL,
                                    related_name="leads")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                              related_name="leads")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = LeadQuerySet.as_manager()

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.parent_name

    @property
    def topic(self):
        return (self.interests.split(",")[0].strip() if self.interests else "") or "coding"

    def schedule_next(self, today):
        """After contacting them: plan the next follow-up, or stop after the last one."""
        if self.follow_ups_sent < len(FOLLOW_UP_DAYS):
            self.next_follow_up = today + timedelta(days=FOLLOW_UP_DAYS[self.follow_ups_sent])
        else:
            self.next_follow_up = None


class LeadEvent(models.Model):
    """What happened with a lead, newest first."""

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="events")
    text = models.CharField(max_length=300)
    by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-at"]
