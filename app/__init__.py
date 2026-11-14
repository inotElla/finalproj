from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail
from config import Config

db = SQLAlchemy()
csrf = CSRFProtect()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "warning"
mail = Mail()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)

    from app import models  # noqa: F401

    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.profile import profile_bp
    from app.routes.staff import staff_bp  # <-- 1. Import staff blueprint

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(staff_bp)       # <-- 2. Register blueprint

    with app.app_context():
        db.create_all()

        # Safely add the columns if they don't exist yet
        try:
            db.session.execute(db.text("ALTER TABLE user ADD COLUMN status VARCHAR(30) DEFAULT 'available'"))
            db.session.commit()
        except Exception:
            db.session.rollback()  # Column already exists, ignore

        try:
            db.session.execute(db.text("ALTER TABLE user ADD COLUMN current_event_id INTEGER"))
            db.session.commit()
        except Exception:
            db.session.rollback()  # Column already exists, ignore

    return app

    return app