from flask import current_app, render_template, url_for
from flask_mail import Message

from app import mail


def external_url(endpoint, **values):
    """Build a full link (https://site/...) for use inside an email.

    If APP_BASE_URL is set, it is used instead of the Host header of the request,
    so a forged Host header cannot change where the link in the email points.
    """
    base_url = current_app.config.get("APP_BASE_URL")
    if base_url:
        return base_url + url_for(endpoint, **values)
    return url_for(endpoint, _external=True, **values)


def send_email(to, subject, template, text, **context):
    """Send one email with a plain-text part and an HTML part.

    template -- name of the file inside templates/email/ (without .html)
    text     -- the plain-text version, for mail apps that do not show HTML
    context  -- variables the HTML template needs
    """
    config = current_app.config

    if not (config.get("MAIL_USERNAME") and config.get("MAIL_PASSWORD")):
        if current_app.debug:
            # Lets you build and test without a real mailbox: the email text is
            # printed in the terminal instead of being sent.
            current_app.logger.warning(
                "Email is not configured. Would have sent to %s | %s\n%s", to, subject, text
            )
            return
        raise RuntimeError("Email is not configured: set MAIL_USERNAME and MAIL_PASSWORD.")

    message = Message(
        subject=subject,
        recipients=[to],
        sender=config.get("MAIL_DEFAULT_SENDER") or config.get("MAIL_USERNAME"),
        body=text,
        html=render_template(f"email/{template}.html", **context),
    )
    mail.send(message)
