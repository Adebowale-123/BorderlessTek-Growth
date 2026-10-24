"""Telegram and email messages to the team."""

import html
import logging

import requests
from django.conf import settings
from django.core.mail import send_mail

from .models import SiteSettings

log = logging.getLogger("apps.core")


def notify(subject, lines):
    """Send a short message (list of lines) to every configured channel. Never raises. Returns channels used."""
    site = SiteSettings.load()
    text = "\n".join(lines)
    sent = []
    if site.telegram_bot_token and site.telegram_chat_id:
        try:
            r = requests.post(f"https://api.telegram.org/bot{site.telegram_bot_token}/sendMessage", timeout=15,
                              json={"chat_id": site.telegram_chat_id, "parse_mode": "HTML",
                                    "text": f"<b>{html.escape(subject)}</b>\n{html.escape(text)}",
                                    "disable_web_page_preview": True})
            if not r.json().get("ok"):
                raise RuntimeError(r.json().get("description", "Telegram error"))
            sent.append("telegram")
        except Exception as exc:
            log.warning("Telegram message failed: %s", exc)
    if site.email_list:
        try:
            send_mail(subject, text, settings.DEFAULT_FROM_EMAIL, site.email_list)
            sent.append("email")
        except Exception as exc:
            log.warning("Email failed: %s", exc)
    return sent
