import smtplib
from email.message import EmailMessage

from flask import current_app, render_template, url_for

SMTP_TIMEOUT_SECONDS = 10  # give up quickly instead of hanging the page


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

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = config.get("MAIL_DEFAULT_SENDER") or config.get("MAIL_USERNAME")
    message["To"] = to
    message.set_content(text)  # plain-text part
    message.add_alternative(render_template(f"email/{template}.html", **context), subtype="html")

    deliver(message)


def deliver(message):
    """Open a connection to the mail server and send one message.

    We talk to the mail server ourselves (instead of Flask-Mail) for one reason: the
    `timeout`. If the host blocks the SMTP port, a plain connection waits forever,
    the web server gives up on the page after 30 seconds and the visitor sees
    "502 Bad Gateway". With a timeout, the attempt fails after a few seconds and the
    page can show a friendly "could not send" message."""
    config = current_app.config
    server_class = smtplib.SMTP_SSL if config.get("MAIL_USE_SSL") else smtplib.SMTP
    with server_class(config["MAIL_SERVER"], config["MAIL_PORT"], timeout=SMTP_TIMEOUT_SECONDS) as server:
        if config.get("MAIL_USE_TLS") and not config.get("MAIL_USE_SSL"):
            server.starttls()
        server.login(config["MAIL_USERNAME"], config["MAIL_PASSWORD"])
        server.send_message(message)

