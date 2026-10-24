from django import forms
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.core.models import SiteSettings

from .models import Opportunity, Source
from .services import add_manual, make_reply


def inbox(request):
    site = SiteSettings.load()
    status = request.GET.get("show", "new")
    qs = Opportunity.objects.select_related("source")
    if status == "new":
        qs = qs.filter(status=Opportunity.Status.NEW, score__gte=site.min_score)
    elif status == "low":
        qs = qs.filter(status=Opportunity.Status.NEW, score__lt=site.min_score)
    elif status in Opportunity.Status.values:
        qs = qs.filter(status=status)
    counts = {"new": Opportunity.objects.filter(status="new", score__gte=site.min_score).count(),
              "low": Opportunity.objects.filter(status="new", score__lt=site.min_score).count(),
              "replied": Opportunity.objects.filter(status="replied").count(),
              "lead": Opportunity.objects.filter(status="lead").count(),
              "dismissed": Opportunity.objects.filter(status="dismissed").count()}
    return render(request, "finder/inbox.html", {"opportunities": qs[:60], "show": status, "counts": counts,
                                                 "manual_form": ManualForm()})


@require_POST
def mark(request, pk, status):
    opp = get_object_or_404(Opportunity, pk=pk)
    if status not in (Opportunity.Status.REPLIED, Opportunity.Status.DISMISSED, Opportunity.Status.NEW):
        return redirect("finder:inbox")
    opp.status = status
    opp.handled_by, opp.handled_at = request.user, timezone.now()
    opp.save(update_fields=["status", "handled_by", "handled_at"])
    if status == Opportunity.Status.REPLIED:
        messages.success(request, "Marked as replied. If they answer, turn them into a lead to track follow-ups.")
    return redirect(request.POST.get("next") or "finder:inbox")


@require_POST
def redraft(request, pk):
    opp = get_object_or_404(Opportunity, pk=pk)
    opp.draft_reply = make_reply(opp)
    opp.save(update_fields=["draft_reply"])
    return redirect(request.POST.get("next") or "finder:inbox")


class ManualForm(forms.Form):
    url = forms.URLField(label="Link to the post", max_length=1000)
    text = forms.CharField(label="What the parent wrote", widget=forms.Textarea(attrs={"rows": 4}),
                           help_text="Paste their message, so the finder can score it and draft a reply.")


@require_POST
def add(request):
    form = ManualForm(request.POST)
    if form.is_valid():
        opp = add_manual(form.cleaned_data["url"], form.cleaned_data["text"], request.user)
        messages.success(request, f"Added, score {opp.score}. A reply is drafted below.")
        return redirect(f"/finder/?show=new#opp-{opp.pk}" if opp.score >= SiteSettings.load().min_score
                        else f"/finder/?show=low#opp-{opp.pk}")
    messages.error(request, "Please add both the link and the text.")
    return redirect("finder:inbox")


class SourceForm(forms.ModelForm):
    class Meta:
        model = Source
        fields = ["kind", "name", "community", "query", "url"]
        labels = {"kind": "Type"}

    def clean(self):
        data = super().clean()
        kind = data.get("kind")
        if kind == Source.Kind.REDDIT and not data.get("query"):
            self.add_error("query", "Add the words to search for.")
        if kind in (Source.Kind.GOOGLE_ALERT, Source.Kind.RSS) and not data.get("url"):
            self.add_error("url", "Paste the feed address.")
        return data


@staff_member_required
def sources(request):
    form = SourceForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Source added. It will be searched on the next scan.")
        return redirect("finder:sources")
    return render(request, "finder/sources.html", {"sources": Source.objects.all(), "form": form})


@staff_member_required
@require_POST
def toggle_source(request, pk):
    source = get_object_or_404(Source, pk=pk)
    source.is_active = not source.is_active
    source.save(update_fields=["is_active"])
    return redirect("finder:sources")


@staff_member_required
@require_POST
def delete_source(request, pk):
    get_object_or_404(Source, pk=pk).delete()
    messages.success(request, "Source removed.")
    return redirect("finder:sources")
