import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()


def env_flag(name, default="false"):
    return os.environ.get(name, default).strip().lower() in ("1", "true", "yes", "on")


def require_env(name):
    """Read a setting that must exist. A missing one stops the app with a clear
    message, instead of a confusing KeyError traceback."""
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"Missing setting {name}. Add it to your .env file (see README.md)."
        )
    return value


class Config:
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
    }

    SECRET_KEY = require_env("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = require_env("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = env_flag("SESSION_COOKIE_SECURE")
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = env_flag("SESSION_COOKIE_SECURE")
    REMEMBER_COOKIE_DURATION = timedelta(days=14)
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    MAX_CONTENT_LENGTH = 1 * 1024 * 1024
    TRUST_PROXY = env_flag("TRUST_PROXY")

    # RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
    # MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "onboarding@resend.dev")

    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", "587"))
    MAIL_USE_TLS = env_flag("MAIL_USE_TLS", "true")
    MAIL_USE_SSL = env_flag("MAIL_USE_SSL", "false")
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER") or MAIL_USERNAME

    APP_BASE_URL = os.environ.get("APP_BASE_URL", "").rstrip("/")
