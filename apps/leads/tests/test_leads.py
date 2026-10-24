from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.finder import scoring
from apps.finder.models import Opportunity
from apps.leads.models import Lead


class LeadTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser("admin", "a@example.com", "pw")
        self.client.force_login(self.user)
        _, s = scoring.score("Animation classes for my 11 year old daughter? Any recommendations")
        self.opp = Opportunity.objects.create(external_id="x", url="https://www.reddit.com/r/Parenting/1", title="Animation?",
                                              author="u/mum", score=80, signals=s, status="replied")

    def test_turn_a_post_into_a_lead_with_follow_ups(self):
        form = self.client.get(reverse("leads:new") + f"?from={self.opp.pk}").context["form"]
        self.assertEqual((form.initial["channel"], form.initial["child_age"], form.initial["stage"]),
                         ("reddit", 11, "contacted"))
        response = self.client.post(reverse("leads:new"), {
            "parent_name": "u/mum", "channel": "reddit", "profile_url": self.opp.url, "child_age": 11,
            "interests": "animation", "stage": "contacted", "opportunity": self.opp.pk})
        lead = Lead.objects.get()
        self.assertRedirects(response, reverse("leads:detail", args=[lead.pk]))
        self.assertEqual(lead.next_follow_up, timezone.localdate() + timedelta(days=2))
        self.opp.refresh_from_db()
        self.assertEqual(self.opp.status, "lead")
        page = self.client.get(reverse("leads:detail", args=[lead.pk]))
        self.assertContains(page, "your 11-year-old")

    def test_follow_up_schedule_then_stop(self):
        lead = Lead.objects.create(parent_name="Sam", stage="contacted", next_follow_up=date(2026, 10, 20))
        self.assertIn(lead, Lead.objects.due(date(2026, 10, 24)))
        for expected_gap in (5, 10, None):
            self.client.post(reverse("leads:followed_up", args=[lead.pk]))
            lead.refresh_from_db()
            if expected_gap:
                self.assertEqual(lead.next_follow_up, timezone.localdate() + timedelta(days=expected_gap))
        self.assertIsNone(lead.next_follow_up)
        self.assertEqual(lead.follow_ups_sent, 3)
        self.assertEqual(lead.events.count(), 3)

    def test_stages_and_board(self):
        lead = Lead.objects.create(parent_name="Jo", stage="contacted", next_follow_up=date(2026, 10, 20))
        self.client.post(reverse("leads:set_stage", args=[lead.pk, "call_booked"]))
        lead.refresh_from_db()
        self.assertEqual((lead.stage, lead.next_follow_up), ("call_booked", None))
        self.client.post(reverse("leads:set_stage", args=[lead.pk, "enrolled"]))
        self.assertContains(self.client.get(reverse("leads:board")), "Jo")
        self.assertNotIn(lead, Lead.objects.open())

    def test_child_age_sanity(self):
        response = self.client.post(reverse("leads:new"), {"parent_name": "X", "channel": "other", "stage": "new",
                                                           "child_age": 40})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Lead.objects.exists())
