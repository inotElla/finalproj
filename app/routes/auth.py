import hashlib
from urllib.parse import urlparse

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user
from flask_mail import Message
from itsdangerous import BadData, URLSafeTimedSerializer

from app import db, mail
from app.forms import (
    LoginForm,
    PasswordResetRequestForm,
    RegistrationForm,
    ResetPasswordForm,
)
from app.models import User

auth_bp = Blueprint("auth", __name__)

RESET_TOKEN_MAX_AGE = 3600  # 1 hour
RESET_SALT = "password-reset"


def is_safe_redirect(target):
    if not target:
        return False
    parts = urlparse(target)
    return (
        parts.scheme == ""
        and parts.netloc == ""
        and target.startswith("/")
        and not target.startswith("//")
        and "\\" not in target
    )


# ---------- Password reset: tokens ----------


def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"])


def _password_stamp(user):
    """A short fingerprint of the user's current password hash.

    It is stored inside the reset token. When the password changes, the
    fingerprint changes too, so a link that was already used stops working.
    """
    return hashlib.sha256(user.password_hash.encode()).hexdigest()[:16]


def make_reset_token(user):
    payload = {"id": user.id, "stamp": _password_stamp(user)}
    return _serializer().dumps(payload, salt=RESET_SALT)


def get_user_from_reset_token(token):
    """Return the user a valid reset token belongs to, or None."""
    try:
        payload = _serializer().loads(
            token, salt=RESET_SALT, max_age=RESET_TOKEN_MAX_AGE
        )
    except BadData:  # tampered, malformed or expired
        return None

    if not isinstance(payload, dict) or not isinstance(payload.get("id"), int):
        return None

    user = db.session.get(User, payload["id"])
    if user is None or payload.get("stamp") != _password_stamp(user):
        return None  # the password already changed, so the link was used
    return user


# ---------- Password reset: email ----------


def build_reset_url(token):
    base_url = current_app.config.get("APP_BASE_URL")
    if base_url:
        return base_url + url_for("auth.reset_password", token=token)
    return url_for("auth.reset_password", token=token, _external=True)


def send_reset_email(user):
    config = current_app.config
    reset_url = build_reset_url(make_reset_token(user))

    if not (config.get("MAIL_USERNAME") and config.get("MAIL_PASSWORD")):
        if current_app.debug:
            # Lets you build and test without a real mailbox: the link is printed
            # in the terminal instead of being emailed.
            current_app.logger.warning(
                "Email is not configured. Reset link for %s: %s", user.email, reset_url
            )
            return
        raise RuntimeError("Email is not configured: set MAIL_USERNAME and MAIL_PASSWORD.")

    minutes = RESET_TOKEN_MAX_AGE // 60
    message = Message(
        subject="Reset your C.A.T.E.R. password",
        recipients=[user.email],
        sender=config.get("MAIL_DEFAULT_SENDER") or config.get("MAIL_USERNAME"),
        body=(
            f"Hi {user.full_name},\n\n"
            "We received a request to reset your C.A.T.E.R. password. "
            f"Open this link within {minutes} minutes. It can only be used once:\n\n"
            f"{reset_url}\n\n"
            "If you did not ask for this, you can ignore this email. "
            "Your password will not change."
        ),
        html=render_template(
            "email/reset_password.html",
            user=user,
            reset_url=reset_url,
            minutes=minutes,
        ),
    )
    mail.send(message)


@auth_bp.route("/reset-password", methods=["GET", "POST"])
def request_password_reset():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user:
            try:
                send_reset_email(user)
            except Exception:
                # Log the real reason, but show the same message either way so the
                # form cannot be used to find out which emails have accounts.
                current_app.logger.exception("Could not send the password reset email")

        flash(
            "If an account exists for that email, a password reset link has been sent.",
            "info",
        )
        return redirect(url_for("auth.login"))

    return render_template("forgot_password.html", form=form)


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    user = get_user_from_reset_token(token)
    if user is None:
        flash("That password reset link is invalid or has expired.", "warning")
        return redirect(url_for("auth.request_password_reset"))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        user.save()
        flash("Your password has been reset. You can now log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("reset_password.html", form=form)


# ---------- Register, log in, log out ----------


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = RegistrationForm()

    if form.validate_on_submit():
        role = "admin" if User.query.count() == 0 else "staff"
        user = User(
            full_name=form.full_name.data.strip(),
            email=form.email.data.lower(),
            role=role,
        )
        user.set_password(form.password.data)
        user.save()
        flash("Account created. You can now log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()

        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get("next")
            if is_safe_redirect(next_page):
                return redirect(next_page)
            return redirect(url_for("main.dashboard"))

        flash("Invalid email or password.", "danger")

    return render_template("login.html", form=form)


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
