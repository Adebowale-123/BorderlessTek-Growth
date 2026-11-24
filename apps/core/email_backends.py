"""Send email through Brevo's HTTPS API.

Render's free web services block outbound SMTP (ports 25, 465 and 587), so Gmail/SMTP can't send from there.
An HTTPS API isn't blocked. Set BREVO_API_KEY and this backend is used automatically (see settings.py).
"""

import logging
from email.utils import parseaddr

import requests
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

log = logging.getLogger(__name__)
API_URL = "https://api.brevo.com/v3/smtp/email"


def _contact(address):
    name, email = parseaddr(address)
    return {"email": email, "name": name} if name else {"email": email}


class BrevoEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        sent = 0
        for message in email_messages:
            recipients = [_contact(a) for a in message.to if a]
            if not recipients:
                continue
            payload = {
                "sender": _contact(message.from_email or settings.DEFAULT_FROM_EMAIL),
                "to": recipients,
                "subject": message.subject,
                "textContent": message.body,
            }
            if message.cc:
                payload["cc"] = [_contact(a) for a in message.cc]
            if message.bcc:
                payload["bcc"] = [_contact(a) for a in message.bcc]
            for content, mimetype in getattr(message, "alternatives", []) or []:
                if mimetype == "text/html":
                    payload["htmlContent"] = content
            try:
                r = requests.post(API_URL, json=payload, timeout=20,
                                  headers={"api-key": settings.BREVO_API_KEY, "accept": "application/json"})
                if r.status_code >= 300:
                    raise RuntimeError(f"Brevo {r.status_code}: {r.text[:300]}")
                sent += 1
            except Exception:
                log.exception("Email to %s failed", [c["email"] for c in recipients])
                if not self.fail_silently:
                    raise
        return sent
