from django import forms
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.core.models import SiteSettings
from apps.finder.models import Opportunity
from apps.finder.replies import follow_up, tracked

from .models import Lead, LeadEvent

CHANNEL_GUESS = {"reddit.com": "reddit", "facebook.com": "facebook", "instagram.com": "instagram",
                 "mumsnet.com": "forum", "netmums.com": "forum"}


class LeadForm(forms.ModelForm):
    class Meta:
        model = Lead
        fields = ["parent_name", "channel", "profile_url", "email", "phone", "country", "child_age", "interests",
                  "consent", "stage", "call_at", "next_follow_up", "notes"]
        widgets = {"call_at": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
                   "next_follow_up": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
                   "notes": forms.Textarea(attrs={"rows": 3})}
        labels = {"consent": "Parent agreed to be contacted by email / WhatsApp", "call_at": "Onboarding call",
                  "next_follow_up": "Next follow-up"}
        help_texts = {"consent": "", "call_at": ""}

    def clean_child_age(self):
        age = self.cleaned_data.get("child_age")
        if age is not None and not 3 <= age <= 19:
            raise forms.ValidationError("Ages 6–16 are our students; please check the age.")
        return age


def board(request):
    q = request.GET.get("q", "").strip()
    leads = Lead.objects.select_related("owner")
    if q:
        leads = leads.filter(parent_name__icontains=q) | leads.filter(email__icontains=q) | \
            leads.filter(notes__icontains=q)
    columns = [(stage, label, [l for l in leads if l.stage == stage]) for stage, label in Lead.Stage.choices]
    return render(request, "leads/board.html", {"columns": columns, "q": q, "today": timezone.localdate()})


def _link(lead, site):
    return tracked(site.booking_url, f"lead-{lead.channel}")


def detail(request, pk=None):
    lead = get_object_or_404(Lead, pk=pk) if pk else None
    initial = {}
    opp = None
    if not lead and request.GET.get("from"):
        opp = get_object_or_404(Opportunity, pk=request.GET["from"])
        host = next((c for d, c in CHANNEL_GUESS.items() if d in opp.url), "other")
        initial = {"parent_name": opp.author or "Parent", "channel": host, "profile_url": opp.url,
                   "child_age": opp.child_age, "interests": ", ".join(opp.signals.get("skills", [])),
                   "stage": Lead.Stage.CONTACTED if opp.status == "replied" else Lead.Stage.NEW}
    form = LeadForm(request.POST or None, instance=lead, initial=initial)
    if request.method == "POST" and form.is_valid():
        is_new = lead is None
        lead = form.save(commit=False)
        if is_new:
            lead.owner = request.user
            if request.POST.get("opportunity"):
                lead.opportunity = Opportunity.objects.filter(pk=request.POST["opportunity"]).first()
            if lead.stage == Lead.Stage.CONTACTED and not lead.next_follow_up:
                lead.schedule_next(timezone.localdate())
        if lead.stage in (Lead.Stage.ENROLLED, Lead.Stage.LOST):
            lead.next_follow_up = None
        lead.save()
        if is_new:
            LeadEvent.objects.create(lead=lead, by=request.user, text="Lead created")
            if lead.opportunity:
                Opportunity.objects.filter(pk=lead.opportunity_id).update(status=Opportunity.Status.LEAD,
                                                                          handled_at=timezone.now())
        else:
            LeadEvent.objects.create(lead=lead, by=request.user, text=f"Updated · {lead.get_stage_display()}")
        messages.success(request, "Saved.")
        return redirect("leads:detail", pk=lead.pk)
    site = SiteSettings.load()
    message = None
    if lead and lead.stage not in (Lead.Stage.ENROLLED, Lead.Stage.LOST):
        message = follow_up(lead.follow_ups_sent, name=lead.parent_name.split()[0] if lead.parent_name else "",
                            topic=lead.topic, age=lead.child_age, link=_link(lead, site))
    return render(request, "leads/detail.html", {"lead": lead, "form": form, "opp": opp or (lead and lead.opportunity),
                                                 "message": message, "events": lead.events.all()[:20] if lead else []})


@require_POST
def followed_up(request, pk):
    """The team sent the follow-up message: count it and plan the next one."""
    lead = get_object_or_404(Lead, pk=pk)
    lead.follow_ups_sent += 1
    if lead.stage == Lead.Stage.NEW:
        lead.stage = Lead.Stage.CONTACTED
    lead.schedule_next(timezone.localdate())
    lead.save()
    nxt = f"next on {lead.next_follow_up:%a %d %b}" if lead.next_follow_up else "no more follow-ups planned"
    LeadEvent.objects.create(lead=lead, by=request.user, text=f"Follow-up {lead.follow_ups_sent} sent · {nxt}")
    messages.success(request, f"Follow-up recorded — {nxt}.")
    return redirect(request.POST.get("next") or reverse("leads:detail", args=[pk]))


@require_POST
def set_stage(request, pk, stage):
    lead = get_object_or_404(Lead, pk=pk)
    if stage not in Lead.Stage.values:
        return redirect("leads:board")
    lead.stage = stage
    if stage in (Lead.Stage.ENROLLED, Lead.Stage.LOST, Lead.Stage.CALL_BOOKED):
        lead.next_follow_up = None
    elif stage == Lead.Stage.CONTACTED and not lead.next_follow_up:
        lead.schedule_next(timezone.localdate())
    lead.save()
    LeadEvent.objects.create(lead=lead, by=request.user, text=f"Moved to {lead.get_stage_display()}")
    if stage == Lead.Stage.ENROLLED:
        messages.success(request, f"🎉 {lead.parent_name} enrolled!")
    return redirect(request.POST.get("next") or "leads:board")
