from urllib.parse import urlparse

from flask import current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user
from flask_wtf.csrf import CSRFError
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from werkzeug.exceptions import HTTPException

from app import db

# One friendly message for each error we expect. Anything else gets the "500" text.
MESSAGES = {
    400: ("Bad request", "We could not understand that request. Please go back and try again."),
    403: ("No access", "You do not have permission to open this page."),
    404: ("Page not found", "The page you are looking for does not exist or was moved."),
    405: ("Not allowed", "That action is not allowed on this page."),
    413: ("Too much data", "What you sent is too large. Please send less and try again."),
    429: ("Too many tries", "Please wait a little before trying again."),
    500: ("Something went wrong", "An unexpected problem happened on our side. Please try again."),
    503: (
        "Database unavailable",
        "We cannot reach the database right now. Please wait a moment and try again.",
    ),
}


def show_error(code):
    title, message = MESSAGES.get(code, MESSAGES[500])
    try:
        signed_in = current_user.is_authenticated
    except Exception:
        signed_in = False
    return render_template(
        "errors/error.html", code=code, title=title, message=message, signed_in=signed_in
    ), code


def came_from_this_site(url):
    """Is `url` a page of our own site? (Never redirect to somebody else's address.)"""
    return bool(url) and urlparse(url).netloc == request.host


def register_error_handlers(app):
    @app.errorhandler(CSRFError)
    def handle_csrf(error):
        flash("Your form expired. Please try again.", "warning") #session expired
        target = request.referrer if came_from_this_site(request.referrer) else url_for("main.index")
        return redirect(target)

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        return show_error(error.code)

    @app.errorhandler(OperationalError)
    def handle_database_down(error):
        # OperationalError = the database could not be reached (lost connection,
        # timeout...). Undo the broken transaction so the next request starts clean.
        db.session.rollback()
        current_app.logger.exception("Database unavailable")
        return show_error(503)

    @app.errorhandler(SQLAlchemyError)
    def handle_database_error(error):
        db.session.rollback()
        current_app.logger.exception("Database error")
        return show_error(500)

    @app.errorhandler(Exception)
    def handle_unexpected(error):
        db.session.rollback()
        if current_app.debug:
            raise error
        current_app.logger.exception("Unhandled error")
        return show_error(500)
