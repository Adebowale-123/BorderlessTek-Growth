import hmac
from datetime import timedelta

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.cache import cache
from django.db.models import Count
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.finder.models import Opportunity, Source
from apps.leads.models import Lead

from . import background
from .models import SiteSettings
from .notify import notify


def healthz(request):
    return HttpResponse("ok", content_type="text/plain")


def _scan_job():
    from apps.finder.services import scan, send_digest

    scan()
    send_digest()


def scan_due(site, now):
    return site.last_scan_at is None or now - site.last_scan_at >= timedelta(hours=site.scan_every_hours)


def tick(request):
    """Called by cron-job.org every 30–60 minutes: scans when due and sends the daily summary. Keeps the site awake."""
    key = settings.TICK_KEY
    given = request.GET.get("key", "").replace(" ", "+")
    if not key or not hmac.compare_digest(given, key):
        return HttpResponseForbidden("bad key")
    site = SiteSettings.load()
    now = timezone.now()
    if scan_due(site, now) and cache.add("scan-lock", True, 600):
        started = background.start("scan", _scan_job)
        return HttpResponse("scan started" if started else "scan already running", content_type="text/plain")
    from apps.finder.services import send_digest

    send_digest()
    return HttpResponse("ok", content_type="text/plain")


def today(request):
    site = SiteSettings.load()
    day = timezone.localdate()
    new = Opportunity.objects.filter(status=Opportunity.Status.NEW, score__gte=site.min_score)
    stages = dict(Lead.objects.values_list("stage").annotate(n=Count("id")))
    week_ago = timezone.now() - timedelta(days=7)
    return render(request, "core/today.html", {
        "hot": new.order_by("-score", "-published_at")[:6],
        "new_count": new.count(), "hot_count": new.filter(score__gte=75).count(),
        "due": Lead.objects.due(day).order_by("next_follow_up")[:8],
        "calls": Lead.objects.filter(stage=Lead.Stage.CALL_BOOKED).order_by("call_at")[:6],
        "pipeline": [(s, label, stages.get(s, 0)) for s, label in Lead.Stage.choices],
        "replied_week": Opportunity.objects.filter(status__in=["replied", "lead"], handled_at__gte=week_ago).count(),
        "leads_week": Lead.objects.filter(created_at__gte=week_ago).count(),
        "enrolled_total": stages.get(Lead.Stage.ENROLLED, 0),
        "sources_count": Source.objects.filter(is_active=True).count(),
        "scanning": background.is_running("scan"),
    })


@require_POST
def scan_now(request):
    if background.start("scan", _scan_job):
        messages.success(request, "Searching for new parent posts now. Refresh in a minute to see them.")
    else:
        messages.info(request, "A search is already running.")
    return redirect(request.POST.get("next") or "core:today")


class SecretInput(forms.PasswordInput):
    def __init__(self):
        super().__init__(render_value=False, attrs={"autocomplete": "off"})


class SettingsForm(forms.ModelForm):
    class Meta:
        model = SiteSettings
        fields = ["company_name", "website_url", "booking_url", "team_member_name", "min_score", "max_age_days",
                  "scan_every_hours", "telegram_bot_token", "telegram_chat_id", "digest_emails", "digest_hour"]
        widgets = {"telegram_bot_token": SecretInput(), "digest_emails": forms.Textarea(attrs={"rows": 3})}
        labels = {"booking_url": "Onboarding call booking link", "team_member_name": "Sign replies as",
                  "min_score": "Minimum score to show", "max_age_days": "Ignore posts older than (days)",
                  "scan_every_hours": "Search every (hours)", "digest_hour": "Daily summary at (hour, UK time)"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.telegram_bot_token:
            self.fields["telegram_bot_token"].help_text = "Saved. Leave blank to keep it."
            self.fields["telegram_bot_token"].required = False

    def clean(self):
        data = super().clean()
        if not data.get("telegram_bot_token"):
            data["telegram_bot_token"] = self.instance.telegram_bot_token
        if data.get("min_score") is not None and data["min_score"] > 100:
            self.add_error("min_score", "0–100.")
        if data.get("digest_hour") is not None and data["digest_hour"] > 23:
            self.add_error("digest_hour", "0–23.")
        if data.get("scan_every_hours") is not None and data["scan_every_hours"] < 1:
            self.add_error("scan_every_hours", "At least 1.")
        return data


@staff_member_required
def settings_page(request):
    form = SettingsForm(request.POST or None, instance=SiteSettings.load())
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Settings saved.")
        return redirect("core:settings")
    return render(request, "core/settings.html", {"form": form, "tick_key_set": bool(settings.TICK_KEY)})


@staff_member_required
@require_POST
def test_alert(request):
    sent = notify("✅ BorderlessTek Growth", ["Alerts are working."])
    if sent:
        messages.success(request, f"Test message sent via {', '.join(sent)}.")
    else:
        messages.error(request, "Nothing sent. Add a Telegram bot token and chat ID, or an email address, then save.")
    return redirect("core:settings")
