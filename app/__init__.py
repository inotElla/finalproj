from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

from config import Config

db = SQLAlchemy()
csrf = CSRFProtect()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "warning"


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)

    from app import models  # noqa: F401

    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)

    with app.app_context():
        db.create_all()

    return app
