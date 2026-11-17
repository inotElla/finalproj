from flask import Flask, request, session
from flask_login import LoginManager
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix

from config import Config

db = SQLAlchemy()
csrf = CSRFProtect()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "warning"
login_manager.session_protection = "strong"  # a session used from a different browser is ended
mail = Mail()


def prepare_database(app):
    """Create missing tables and add the columns that were added later.

    create_all() never changes a table that already exists, so newer columns are
    added by hand. If a column is already there the database says so, and we just
    undo and carry on."""
    db.create_all()

    for statement in (
        "ALTER TABLE user ADD COLUMN status VARCHAR(30) DEFAULT 'available'",
        "ALTER TABLE user ADD COLUMN current_event_id INTEGER",
        "ALTER TABLE event ADD COLUMN end_time TIME NULL",
        "ALTER TABLE event_equipment ADD COLUMN packed BOOLEAN NOT NULL DEFAULT 0",
        "ALTER TABLE event_equipment ADD COLUMN returned_quantity INTEGER NULL",
        "ALTER TABLE event_equipment ADD COLUMN issue_note VARCHAR(200) NULL",
    ):
        try:
            db.session.execute(db.text(statement))
            db.session.commit()
        except Exception:
            db.session.rollback()  # column already exists, ignore


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    if app.config["TRUST_PROXY"]:
        # Render sits in front of the app. This makes request.remote_addr the visitor's
        # real address and makes links use https.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)

    from app import models  # noqa: F401

    from app.errors import register_error_handlers
    from app.routes.activity import activity_bp
    from app.routes.auth import auth_bp
    from app.routes.checklists import checklists_bp
    from app.routes.equipment import equipment_bp
    from app.routes.events import events_bp
    from app.routes.main import main_bp
    from app.routes.profile import profile_bp
    from app.routes.staff import staff_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(staff_bp)
    app.register_blueprint(equipment_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(checklists_bp)
    app.register_blueprint(activity_bp)

    register_error_handlers(app)

    @app.before_request
    def keep_event_statuses_current():
        # Before showing a page to a signed-in person, make sure event statuses match the
        # clock (see app/event_status.py). It does real work at most once a minute.
        if "_user_id" not in session or request.endpoint in (None, "static"):
            return
        try:
            from app.event_status import refresh_event_statuses

            refresh_event_statuses()
        except Exception:
            db.session.rollback()
            app.logger.exception("Could not refresh event statuses")

    @app.after_request
    def add_security_headers(response):
        # Tell the browser not to guess file types, not to show us inside another
        # site's frame (clickjacking), and to share little in the Referer header.
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Pages of a signed-in person are not kept by the browser, so pressing Back
        # after logging out cannot show them again. ("_user_id" is Flask-Login's
        # session key; checking it avoids a database lookup.)
        if "_user_id" in session:
            response.headers["Cache-Control"] = "no-store"
        return response

    # If the database is unreachable at start-up the app still starts, and every
    # page then shows the friendly "Database unavailable" message.
    with app.app_context():
        try:
            prepare_database(app)
        except Exception:
            db.session.rollback()
            app.logger.exception("Could not prepare the database at start-up")

    return app
