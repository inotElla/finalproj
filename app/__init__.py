from flask import Flask, request, session
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_mail import Mail           
from config import Config

db = SQLAlchemy()
csrf = CSRFProtect()
login_manager = LoginManager()
mail = Mail()                        
login_manager.login_view = "auth.login"
login_manager.login_message_category = "warning"
login_manager.session_protection = "strong" 


def prepare_database(app):
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
            db.session.rollback()  


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    if app.config["TRUST_PROXY"]:
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
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        if "_user_id" in session:
            response.headers["Cache-Control"] = "no-store"
        return response

    with app.app_context():
        try:
            prepare_database(app)
        except Exception:
            db.session.rollback()
            app.logger.exception("Could not prepare the database at start-up")

    return app
