"""Sends email through the Brevo web API (works on Render, where normal SMTP is often blocked).

Set these in Render, Environment:
  BREVO_API_KEY   the API key from your Brevo account
  MAIL_FROM       a sender address verified in Brevo, e.g. promis@yourdomain.com
  MAIL_FROM_NAME  optional, default "SDLG-Production MIS"
"""
import base64
import json
import logging
import os
import urllib.error
import urllib.request

log = logging.getLogger(__name__)
API = "https://api.brevo.com/v3/smtp/email"


def is_configured():
    return bool(os.environ.get("BREVO_API_KEY") and os.environ.get("MAIL_FROM"))


def send_email(to, subject, text, html=None, attachments=None, cc=None):
    """to / cc: a string or a list of addresses. attachments: list of (filename, bytes).
    Returns (True, "") on success, otherwise (False, reason). Never raises."""
    if not is_configured():
        log.warning("Email not sent (BREVO_API_KEY / MAIL_FROM not set): %s", subject)
        return False, "Email is not set up yet (BREVO_API_KEY and MAIL_FROM are missing)."
    if isinstance(to, str):
        to = [to]
    if isinstance(cc, str):
        cc = [cc]
    to = [t.strip() for t in to if t and t.strip()]
    if not to:
        return False, "No recipient address."

    payload = {
        "sender": {
            "email": os.environ["MAIL_FROM"],
            "name": os.environ.get("MAIL_FROM_NAME", "SDLG-Production MIS"),
        },
        "to": [{"email": t} for t in to],
        "subject": subject,
        "textContent": text,
    }
    if html:
        payload["htmlContent"] = html
    if cc:
        payload["cc"] = [{"email": c.strip()} for c in cc if c and c.strip()]
    if attachments:
        payload["attachment"] = [
            {"name": name, "content": base64.b64encode(data).decode("ascii")}
            for name, data in attachments
        ]
    req = urllib.request.Request(
        API,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "api-key": os.environ["BREVO_API_KEY"],
            "content-type": "application/json",
            "accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30):
            return True, ""
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:300]
        log.error("Brevo rejected the email (%s): %s", e.code, body)
        return False, "Email service said %s: %s" % (e.code, body)
    except Exception as e:  # network down, timeout
        log.error("Email could not be sent: %s", e)
        return False, str(e)
