import smtplib
from email.message import EmailMessage

from flask import current_app, render_template, url_for

SMTP_TIMEOUT_SECONDS = 10


def external_url(endpoint, **values):
    base_url = current_app.config.get("APP_BASE_URL")
    if base_url:
        return base_url + url_for(endpoint, **values)
    return url_for(endpoint, _external=True, **values)


def send_email(to, subject, template, text, **context):
    config = current_app.config

    if not (config.get("MAIL_USERNAME") and config.get("MAIL_PASSWORD")):
        if current_app.debug:
            current_app.logger.warning(
                "Email is not configured. Would have sent to %s | %s\n%s", to, subject, text
            )
            return
        raise RuntimeError("Email is not configured: set MAIL_USERNAME and MAIL_PASSWORD.")

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = config.get("MAIL_DEFAULT_SENDER") or config.get("MAIL_USERNAME")
    message["To"] = to
    message.set_content(text)
    message.add_alternative(render_template(f"email/{template}.html", **context), subtype="html")

    deliver(message)


def deliver(message):
    config = current_app.config
    server_class = smtplib.SMTP_SSL if config.get("MAIL_USE_SSL") else smtplib.SMTP
    with server_class(config["MAIL_SERVER"], config["MAIL_PORT"], timeout=SMTP_TIMEOUT_SECONDS) as server:
        if config.get("MAIL_USE_TLS") and not config.get("MAIL_USE_SSL"):
            server.starttls()
        server.login(config["MAIL_USERNAME"], config["MAIL_PASSWORD"])
        server.send_message(message)