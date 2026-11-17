import requests  # ← CHANGED: was "import smtplib" — we now use HTTP, not SMTP

from flask import current_app, render_template, url_for

#HTTPS (port 443)
RESEND_API_URL = "https://api.resend.com/emails"
RESEND_TIMEOUT = 10


def external_url(endpoint, **values):
    base_url = current_app.config.get("APP_BASE_URL")
    if base_url:
        return base_url + url_for(endpoint, **values)
    return url_for(endpoint, _external=True, **values)


def send_email(to, subject, template, text, **context):
    config = current_app.config

    api_key = config.get("RESEND_API_KEY")
    if not api_key:
        if current_app.debug:
            current_app.logger.warning(
                "RESEND_API_KEY is not set. Would have sent to %s | %s\n%s",
                to, subject, text,
            )
            return
        raise RuntimeError("Email is not configured: set RESEND_API_KEY.")

    sender = config.get("MAIL_DEFAULT_SENDER", "onboarding@resend.dev")

    html_body = render_template(f"email/{template}.html", **context)


    deliver(api_key, sender, to, subject, text, html_body)

def deliver(api_key, sender, to, subject, text, html):

    response = requests.post(
        RESEND_API_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "from": sender,
            "to": [to],
            "subject": subject,
            "text": text,
            "html": html,
        },
        timeout=RESEND_TIMEOUT,
    )
    response.raise_for_status()
