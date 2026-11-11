import os

from dotenv import load_dotenv

load_dotenv()


def env_flag(name, default="false"):
    """Read a true/false setting from the environment."""
    return os.environ.get(name, default).strip().lower() in ("1", "true", "yes", "on")


class Config:
    
    SECRET_KEY = os.environ["SECRET_KEY"]
    SQLALCHEMY_DATABASE_URI = os.environ["DATABASE_URL"]
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", "587"))
    MAIL_USE_TLS = env_flag("MAIL_USE_TLS", "true")
    MAIL_USE_SSL = env_flag("MAIL_USE_SSL", "false")
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER") or MAIL_USERNAME

    # Optional: the public address of the site, for example https://cater.onrender.com
    # When set, links inside emails always use it instead of the address the
    # visitor typed, which stops forged "Host" headers from poisoning reset links.
    #APP_BASE_URL = os.environ.get("APP_BASE_URL", "").rstrip("/")

