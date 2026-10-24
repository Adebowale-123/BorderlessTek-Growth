from django.core.management.base import BaseCommand

from apps.finder import scoring
from apps.finder.models import Opportunity
from apps.finder.services import make_reply


class Command(BaseCommand):
    help = "Re-score posts still waiting for a reply (after the scoring rules change) and refresh their drafts."

    def handle(self, *args, **options):
        changed = 0
        for opp in Opportunity.objects.filter(status=Opportunity.Status.NEW):
            points, signals = scoring.score(f"{opp.title}\n{opp.body}")
            if points != opp.score or signals != opp.signals:
                opp.score, opp.signals = points, signals
                opp.draft_reply = make_reply(opp)
                opp.save(update_fields=["score", "signals", "draft_reply"])
                changed += 1
        self.stdout.write(self.style.SUCCESS(f"Re-scored {changed} post(s)."))
