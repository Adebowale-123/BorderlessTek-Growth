from datetime import datetime, timedelta, timezone
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.core.models import SiteSettings
from apps.finder import replies, scoring, services
from apps.finder.models import Opportunity, Source

UTC = timezone.utc
NOW = datetime(2026, 10, 24, 12, 0, tzinfo=UTC)


class ScoringTests(TestCase):
    def test_parent_asking_for_classes_is_hot(self):
        points, s = scoring.score("Coding classes for my 10 year old? My son loves Minecraft and wants to learn to "
                                  "code. Any recommendations for online classes in the UK?")
        self.assertGreaterEqual(points, 75)
        self.assertEqual(s["ages"], [10])
        self.assertIn("coding", s["skills"])

    def test_real_false_positives_stay_below_the_threshold(self):
        # From the first real scan
        for text in ["Need a spell for a job. I'm 34 and my career needs help, any advice? Dress code is strict.",
                     "Lewisham Loop - Issue 40: bees, beats and classes for ages 16 and up. Any suggestions welcome.",
                     "Seeing my kid build something from scratch is so cool"]:
            points, _ = scoring.score(text)
            self.assertLess(points, 45, text)

    def test_scratch_means_the_coding_tool_only_in_context(self):
        self.assertIn("scratch", scoring.detect("my daughter uses Scratch at school")["skills"])
        self.assertIn("scratch", scoring.detect("any good scratch projects for a 7 yo?")["skills"])
        self.assertNotIn("scratch", scoring.detect("we baked a cake from scratch")["skills"])

    def test_adults_and_ads_and_wrong_ages(self):
        adult, _ = scoring.score("I'm 28, career change, looking for a coding bootcamp for me, any recommendations?")
        ad, _ = scoring.score("[HIRING] coding tutor for kids, use my code for a discount, my son approved")
        toddler, s = scoring.score("Coding apps for my 3 year old? Any recommendations?")
        self.assertLess(adult, 45)
        self.assertLess(ad, 45)
        self.assertLess(toddler, 75)
        self.assertIn("Age outside 6–16", s["reasons"])

    def test_mumsnet_style_and_school_years(self):
        points, s = scoring.score("DS (Year 6) is obsessed with making games. Where can we find a good coding club?")
        self.assertGreaterEqual(points, 60)
        self.assertIn(11, s["ages"])


class ReplyTests(TestCase):
    def test_reply_is_helpful_honest_and_tracked(self):
        _, s = scoring.score("Animation classes for my 13 year old daughter? Recommendations please")
        text = replies.draft(s, company="BorderlessTek", name="Ada", booking_url="https://calendly.com/bt/onboarding",
                             source="reddit-parenting", seed="abc")
        self.assertIn("13-year-old", text)
        self.assertIn("Blender", text)  # an age-appropriate tip, not just a pitch
        self.assertIn("Full disclosure: I work with BorderlessTek", text)
        self.assertIn("utm_source=reddit-parenting", text)
        self.assertTrue(text.rstrip().endswith("Ada"))

    def test_without_a_booking_link_it_offers_to_share_more(self):
        text = replies.draft({"skills": ["coding"], "ages": []}, booking_url="", seed="x")
        self.assertIn("Happy to share more", text)
        self.assertIn("your child", text)

    def test_follow_ups_get_gentler_and_stop(self):
        first = replies.follow_up(0, name="Sam", topic="coding", age=9, link="L")
        last = replies.follow_up(5, name="Sam", link="L")
        self.assertIn("your 9-year-old", first)
        self.assertIn("I won't keep messaging", last)


ATOM = b"""<?xml version="1.0" encoding="UTF-8"?><feed xmlns="http://www.w3.org/2005/Atom">
<entry><id>t3_abc</id><title>Coding classes for my 9 year old?</title>
<link href="https://www.reddit.com/r/UKParenting/comments/abc/coding_classes/"/><author><name>/u/kentmum</name></author>
<category term="UKParenting" label="r/UKParenting"/><updated>2026-10-24T09:00:00+00:00</updated>
<content type="html">&lt;p&gt;My son loves Roblox and wants to learn coding. Any recommendations for online classes?&lt;/p&gt;</content></entry>
<entry><id>t3_old</id><title>Coding classes for my 9 year old?</title><link href="https://www.reddit.com/r/x/old/"/>
<updated>2026-08-01T09:00:00+00:00</updated><content type="html">My son, any recommendations for coding classes?</content></entry>
<entry><id>t3_off</id><title>Best pizza in town</title><link href="https://www.reddit.com/r/x/pizza/"/>
<updated>2026-10-24T09:00:00+00:00</updated><content type="html">Recommendations?</content></entry>
</feed>"""


def fake_get(status=200, content=ATOM):
    response = mock.Mock(status_code=status, content=content)
    return mock.patch("apps.finder.services.requests.get", return_value=response)


class ScanTests(TestCase):
    def setUp(self):
        SiteSettings.objects.update_or_create(pk=1, defaults={"booking_url": "https://calendly.com/bt/call",
                                                              "team_member_name": "Ada"})
        self.source = Source.objects.create(name="Parents", kind="reddit", community="UKParenting", query="coding")

    def test_scan_keeps_fresh_relevant_posts_once(self):
        with fake_get(), mock.patch.object(services, "PAUSE_SECONDS", 0):
            summary = services.scan(now=NOW)
            again = services.scan(now=NOW)
        self.assertEqual((summary["found"], again["found"]), (1, 0))
        opp = Opportunity.objects.get()
        self.assertEqual((opp.community, opp.author, opp.child_age), ("r/UKParenting", "u/kentmum", 9))
        self.assertIn("utm_source=reddit-ukparenting", opp.draft_reply)
        self.assertIn("Full disclosure", opp.draft_reply)
        self.source.refresh_from_db()
        self.assertEqual(self.source.found_count, 1)

    def test_rate_limit_is_recorded_not_crashing(self):
        with fake_get(status=429):
            summary = services.scan(now=NOW)
        self.assertEqual(summary["errors"], 1)
        self.source.refresh_from_db()
        self.assertIn("slow down", self.source.last_error)

    def test_after_a_429_other_reddit_sources_wait_their_turn(self):
        second = Source.objects.create(name="More parents", kind="reddit", community="Mommit", query="coding")
        with fake_get(status=429) as get, mock.patch.object(services, "PAUSE_SECONDS", 0):
            services.scan(now=NOW)
        self.assertEqual(get.call_count, 1)  # stopped asking after Reddit said slow down
        second.refresh_from_db()
        self.source.refresh_from_db()
        with fake_get() as get, mock.patch.object(services, "PAUSE_SECONDS", 0):
            services.scan(now=NOW + timedelta(hours=3))
        self.assertIn("/r/Mommit/", get.call_args_list[0].args[0])  # the one that missed out goes first

    def test_feed_url_and_google_alert_links(self):
        self.assertIn("/r/UKParenting/search.rss?q=coding&restrict_sr=1", self.source.feed_url)
        multi = Source(kind="reddit", community="Parenting+Mommit", query='"my son" coding')
        self.assertIn("/r/Parenting+Mommit/search.rss?q=%22my+son%22+coding", multi.feed_url)
        self.assertEqual(services.real_url("https://www.google.com/url?rct=j&sa=t&url=https://mumsnet.com/t/1&ct=ga"),
                         "https://mumsnet.com/t/1")

    def test_manual_post(self):
        opp = services.add_manual("https://facebook.com/groups/x/posts/1",
                                  "Looking for a coding club for my 12 year old daughter, any recommendations?")
        self.assertTrue(opp.manual)
        self.assertGreaterEqual(opp.score, 75)
        self.assertIn("12-year-old", opp.draft_reply)


class DigestTests(TestCase):
    def test_once_a_day_after_the_hour(self):
        SiteSettings.objects.update_or_create(pk=1, defaults={"digest_hour": 8})
        with mock.patch("apps.core.notify.notify", return_value=["telegram"]) as notify:
            early = services.send_digest(now=datetime(2026, 10, 24, 6, 0, tzinfo=UTC))  # 07:00 UK
            first = services.send_digest(now=datetime(2026, 10, 24, 9, 0, tzinfo=UTC))
            second = services.send_digest(now=datetime(2026, 10, 24, 15, 0, tzinfo=UTC))
        self.assertEqual((early, first, second), ([], ["telegram"], []))
        self.assertEqual(notify.call_count, 1)


class PageTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser("admin", "a@example.com", "pw")
        self.client.force_login(self.admin)
        _, s = scoring.score("Coding classes for my 10 year old son? Recommendations please, online")
        self.opp = Opportunity.objects.create(external_id="x1", url="https://reddit.com/r/x/1", title="Coding for my 10yo?",
                                              score=80, signals=s, draft_reply="Hello!", community="r/Parenting")

    def test_pages_render(self):
        for name in ("core:today", "finder:inbox", "finder:sources", "leads:board", "core:settings", "leads:new"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)
        self.assertContains(self.client.get(reverse("finder:inbox")), "Coding for my 10yo?")

    def test_reply_dismiss_and_privacy(self):
        self.client.post(reverse("finder:mark", args=[self.opp.pk, "replied"]))
        self.opp.refresh_from_db()
        self.assertEqual(self.opp.status, "replied")
        self.client.logout()
        self.assertEqual(self.client.get(reverse("finder:inbox")).status_code, 302)

    @override_settings(TICK_KEY="secret")
    def test_tick_needs_the_key(self):
        self.client.logout()
        self.assertEqual(self.client.get("/tick/?key=wrong").status_code, 403)
        with mock.patch("apps.core.background.start", return_value=True):
            self.assertEqual(self.client.get("/tick/?key=secret").status_code, 200)
