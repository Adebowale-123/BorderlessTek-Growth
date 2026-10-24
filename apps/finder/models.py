from urllib.parse import quote_plus

from django.conf import settings
from django.db import models


class Source(models.Model):
    """Where to look for parents' questions."""

    class Kind(models.TextChoices):
        REDDIT = "reddit", "Reddit community search"
        GOOGLE_ALERT = "google_alert", "Google Alert (RSS)"
        RSS = "rss", "Any RSS / Atom feed"

    name = models.CharField(max_length=80)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.REDDIT)
    community = models.CharField(max_length=300, blank=True,
                                 help_text="Reddit communities without r/, joined with +, e.g. Parenting+Mommit. Empty = all of Reddit.")
    query = models.CharField(max_length=300, blank=True, help_text="Words to search for (Reddit).")
    url = models.URLField(max_length=600, blank=True, help_text="Feed address (Google Alert or RSS).")
    is_active = models.BooleanField(default=True)
    last_checked = models.DateTimeField(null=True, blank=True)
    last_error = models.CharField(max_length=255, blank=True)
    found_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["kind", "name"]

    def __str__(self):
        return self.name

    @property
    def feed_url(self):
        if self.kind == self.Kind.REDDIT:
            q = quote_plus(self.query or "coding")
            base = f"https://www.reddit.com/r/{self.community}/search.rss" if self.community else \
                "https://www.reddit.com/search.rss"
            return f"{base}?q={q}&restrict_sr={'1' if self.community else '0'}&sort=new&t=month"
        return self.url

    @property
    def label(self):
        if self.kind == self.Kind.REDDIT and self.community and "+" not in self.community:
            return f"r/{self.community}"
        return self.name


class Opportunity(models.Model):
    """A public post where a parent may be looking for what BorderlessTek teaches."""

    class Status(models.TextChoices):
        NEW = "new", "New"
        REPLIED = "replied", "Replied"
        LEAD = "lead", "Became a lead"
        DISMISSED = "dismissed", "Not relevant"

    source = models.ForeignKey(Source, null=True, blank=True, on_delete=models.SET_NULL, related_name="opportunities")
    external_id = models.CharField(max_length=300, unique=True)
    url = models.URLField(max_length=1000)
    title = models.CharField(max_length=300)
    body = models.TextField(blank=True)
    author = models.CharField(max_length=120, blank=True)
    community = models.CharField(max_length=120, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    found_at = models.DateTimeField(auto_now_add=True)
    score = models.PositiveSmallIntegerField(default=0, db_index=True)
    signals = models.JSONField(default=dict, blank=True)
    draft_reply = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.NEW, db_index=True)
    handled_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                   related_name="+")
    handled_at = models.DateTimeField(null=True, blank=True)
    manual = models.BooleanField(default=False, help_text="Added by hand (e.g. from a Facebook group).")

    class Meta:
        ordering = ["-score", "-published_at"]

    def __str__(self):
        return self.title[:80]

    @property
    def heat(self):
        return "hot" if self.score >= 75 else "warm" if self.score >= 55 else "mild"

    @property
    def child_age(self):
        ages = [a for a in self.signals.get("ages", []) if 6 <= a <= 16]
        return ages[0] if ages else None

    @property
    def skill(self):
        skills = self.signals.get("skills") or []
        return skills[0] if skills else ""
