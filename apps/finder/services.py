"""Scanning sources for parents' questions, scoring them, drafting replies, and the daily summary."""

import html
import logging
import re
import time as time_module
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import feedparser
import requests
from django.db import IntegrityError
from django.db.models import F
from django.utils import timezone as dj_tz

from apps.core.models import SiteSettings

from . import replies, scoring
from .models import Opportunity, Source

log = logging.getLogger("apps.finder")
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; BorderlessTek-LeadFinder/1.0; human-reviewed replies)"}
PAUSE_SECONDS = 30  # Reddit lets anonymous readers ask about twice a minute; a full scan runs in the background


class FeedError(Exception):
    pass


def clean(text):
    """Feed HTML -> readable plain text."""
    text = re.sub(r"<br\s*/?>|</p>|</li>", "\n", text or "", flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\[link\]|\[comments\]|submitted by\s+/u/\S+", " ", text)
    return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n\n", text)).strip()


def real_url(link):
    """Google Alerts wraps links as google.com/url?...&url=REAL; unwrap them."""
    parsed = urlparse(link or "")
    if parsed.netloc.endswith("google.com") and parsed.path == "/url":
        target = parse_qs(parsed.query).get("url")
        if target:
            return target[0]
    return link


def fetch(source):
    """Download and parse one source. Returns a list of plain dicts."""
    try:
        response = requests.get(source.feed_url, headers=HEADERS, timeout=25)
    except requests.RequestException as exc:
        raise FeedError(f"Could not reach the feed ({exc.__class__.__name__})") from exc
    if response.status_code == 429:
        raise FeedError("The site asked us to slow down (429). It will be tried again on the next scan.")
    if response.status_code != 200:
        raise FeedError(f"Feed answered {response.status_code}")
    feed = feedparser.parse(response.content)
    items = []
    for e in feed.entries:
        body = ""
        if e.get("content"):
            body = e.content[0].get("value", "")
        body = body or e.get("summary", "")
        published = e.get("published_parsed") or e.get("updated_parsed")
        author = e.get("author", "")
        items.append({
            "id": e.get("id") or e.get("link"),
            "url": real_url(e.get("link", "")),
            "title": clean(e.get("title", ""))[:300],
            "body": clean(body)[:5000],
            "author": author.replace("/u/", "u/")[:120],
            "community": (e.get("tags") or [{}])[0].get("label", "") if e.get("tags") else "",
            "published": datetime(*published[:6], tzinfo=timezone.utc) if published else None,
        })
    return items


def make_reply(opportunity, site=None):
    site = site or SiteSettings.load()
    source = (opportunity.source.label if opportunity.source else "manual").replace("r/", "reddit-").lower()
    return replies.draft(opportunity.signals, company=site.company_name, name=site.team_member_name,
                         booking_url=site.booking_url, source=source, seed=opportunity.external_id)


def save_item(item, source, site, now):
    """Score and store one post. Returns the Opportunity if it is new and relevant enough, else None."""
    if not item.get("url") or not item.get("id"):
        return None
    if item["published"] and now - item["published"] > timedelta(days=site.max_age_days):
        return None
    if Opportunity.objects.filter(external_id=item["id"][:300]).exists():
        return None
    points, signals = scoring.score(f"{item['title']}\n{item['body']}")
    # Keep near-misses (so the threshold can be lowered later), but never posts about something else entirely.
    if not signals["skills"] or points < max(25, site.min_score - 20):
        return None
    opp = Opportunity(source=source, external_id=item["id"][:300], url=item["url"][:1000], title=item["title"] or "(no title)",
                      body=item["body"], author=item["author"], community=item["community"] or (source.label if source else ""),
                      published_at=item["published"], score=points, signals=signals)
    opp.draft_reply = make_reply(opp, site)
    try:
        opp.save()
    except IntegrityError:
        return None
    return opp


def scan(sources=None, now=None):
    """Check every active source once. Returns a summary dict."""
    site = SiteSettings.load()
    now = now or dj_tz.now()
    found, errors = 0, 0
    if sources is None:  # stalest first, so every source gets its turn even when a site limits us
        sources = Source.objects.filter(is_active=True).order_by(F("last_checked").asc(nulls_first=True))
    sources = list(sources)
    reddit_paused = False
    for i, source in enumerate(sources):
        if source.kind == Source.Kind.REDDIT and reddit_paused:
            continue  # Reddit asked us to slow down: leave the rest for the next scan
        if i:
            time_module.sleep(PAUSE_SECONDS)
        try:
            items = fetch(source)
        except FeedError as exc:
            source.last_error = str(exc)[:255]
            source.last_checked = now
            source.save(update_fields=["last_error", "last_checked"])
            errors += 1
            if source.kind == Source.Kind.REDDIT and "429" in str(exc):
                reddit_paused = True
            continue
        new = [opp for opp in (save_item(item, source, site, now) for item in items) if opp]
        source.found_count += len(new)
        source.last_error = ""
        source.last_checked = now
        source.save(update_fields=["found_count", "last_error", "last_checked"])
        found += len(new)
    SiteSettings.objects.filter(pk=site.pk).update(last_scan_at=now)
    log.info("Scan: %s new opportunities from %s sources (%s errors)", found, len(sources), errors)
    return {"found": found, "sources": len(sources), "errors": errors}


def add_manual(url, text, user=None):
    """A post your team found themselves (e.g. in a Facebook group)."""
    site = SiteSettings.load()
    points, signals = scoring.score(text)
    first_line = (text.strip().splitlines() or ["Manual post"])[0][:300]
    opp, _ = Opportunity.objects.get_or_create(
        external_id=f"manual:{url}"[:300],
        defaults=dict(url=url, title=first_line, body=text[:5000], score=points, signals=signals, manual=True,
                      community=urlparse(url).netloc.replace("www.", "")[:120], published_at=dj_tz.now()))
    if not opp.draft_reply:
        opp.draft_reply = make_reply(opp, site)
        opp.save(update_fields=["draft_reply"])
    return opp


# ---------------------------------------------------------------------------
# Daily summary
# ---------------------------------------------------------------------------


def digest_text(site, today):
    from apps.leads.models import Lead

    new = Opportunity.objects.filter(status=Opportunity.Status.NEW, score__gte=site.min_score)
    hot = new.filter(score__gte=75).count()
    due = Lead.objects.due(today).count()
    calls = Lead.objects.filter(stage=Lead.Stage.CALL_BOOKED).count()
    week = Lead.objects.filter(created_at__date__gte=today - timedelta(days=7)).count()
    return [f"Good morning! Here's {site.company_name}'s growth summary:",
            f"• {new.count()} parents to reply to ({hot} hot)",
            f"• {due} follow-ups due today",
            f"• {calls} onboarding calls booked",
            f"• {week} new leads in the last 7 days"]


def send_digest(force=False, now=None):
    """Send the daily summary once a day (after the chosen hour, UK time). Returns the channels used."""
    from apps.core.notify import notify

    site = SiteSettings.load()
    now = now or dj_tz.now()
    local = dj_tz.localtime(now)
    if not force and (site.last_digest_on == local.date() or local.hour < site.digest_hour):
        return []
    sent = notify(f"{site.company_name} growth summary", digest_text(site, local.date()))
    SiteSettings.objects.filter(pk=site.pk).update(last_digest_on=local.date())
    return sent
