def branding(request):
    """Company name and today's counts for the menu badges."""
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return {}
    from django.utils import timezone

    from apps.finder.models import Opportunity
    from apps.leads.models import Lead

    from .models import SiteSettings

    site = SiteSettings.load()
    return {
        "site": site,
        "nav_new": Opportunity.objects.filter(status=Opportunity.Status.NEW, score__gte=site.min_score).count(),
        "nav_due": Lead.objects.due(timezone.localdate()).count(),
    }
