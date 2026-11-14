import hashlib

from flask import Blueprint, current_app, flash, redirect, render_template, url_for
from flask_login import current_user, login_required
from itsdangerous import BadData, URLSafeTimedSerializer
from sqlalchemy.exc import IntegrityError

from app import db
from app.emailer import external_url, send_email
from app.forms import ChangeEmailForm, ChangePasswordForm, ProfileNameForm
from app.models import User

profile_bp = Blueprint("profile", __name__, url_prefix="/profile")

EMAIL_TOKEN_MAX_AGE = 3600  # the confirmation link works for 1 hour
EMAIL_SALT = "email-change"  # a different salt means a reset-password token can never be used here


# ---------- Email-change token ----------


def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"])


def _email_stamp(user):
    # A short fingerprint of the CURRENT email. Once the email changes, the
    # fingerprint changes too, so the same link cannot be used a second time.
    return hashlib.sha256(user.email.encode()).hexdigest()[:16]


def make_email_token(user, new_email):
    payload = {"id": user.id, "new": new_email, "stamp": _email_stamp(user)}
    return _serializer().dumps(payload, salt=EMAIL_SALT)


def read_email_token(token, user):
    """Return the new email from a valid token that belongs to this user, else None."""
    try:
        payload = _serializer().loads(token, salt=EMAIL_SALT, max_age=EMAIL_TOKEN_MAX_AGE)
    except BadData:  # bad signature, expired, garbled...
        return None

    if (
        not isinstance(payload, dict)
        or payload.get("id") != user.id
        or not isinstance(payload.get("new"), str)
        or payload.get("stamp") != _email_stamp(user)
    ):
        return None
    return payload["new"]


# ---------- Helpers ----------


def render_profile(name_form=None, email_form=None, password_form=None, open_section=None):
    """Show the profile page. A form that failed validation is passed in so its
    errors are displayed; the other forms are created fresh and empty.

    open_section ("name", "email" or "password") is the section whose form should
    start open, so the user sees the errors. Every other form stays closed until
    the user presses its Change button."""
    if name_form is None:
        # formdata=None means "do not read request.form": the form starts from the saved name.
        name_form = ProfileNameForm(formdata=None, obj=current_user)
    if email_form is None:
        email_form = ChangeEmailForm(formdata=None)
    if password_form is None:
        password_form = ChangePasswordForm(formdata=None)

    return render_template(
        "profile.html",
        name_form=name_form,
        email_form=email_form,
        password_form=password_form,
        open_section=open_section,
    )


def notify(to, subject, template, text, **context):
    """Send a security notice. A failure is logged and never blocks the user's change."""
    try:
        send_email(to, subject, template, text, **context)
    except Exception:
        current_app.logger.exception("Could not send the '%s' email", subject)


# ---------- Routes ----------


@profile_bp.route("/")
@login_required
def show_profile():
    return render_profile()


@profile_bp.route("/name", methods=["POST"])
@login_required
def update_name():
    form = ProfileNameForm()
    if form.validate_on_submit():
        # " ".join(x.split()) collapses extra spaces: "Ella   Arevalo " -> "Ella Arevalo"
        current_user.full_name = " ".join(form.full_name.data.split())
        current_user.save()
        flash("Your name has been updated.", "success")
        return redirect(url_for("profile.show_profile"))

    return render_profile(name_form=form, open_section="name")


@profile_bp.route("/email", methods=["POST"])
@login_required
def request_email_change():
    form = ChangeEmailForm()
    if form.validate_on_submit():
        new_email = form.new_email.data.strip().lower()
        minutes = EMAIL_TOKEN_MAX_AGE // 60
        confirm_url = external_url(
            "profile.confirm_email", token=make_email_token(current_user, new_email)
        )

        try:
            send_email(
                new_email,
                "Confirm your new C.A.T.E.R. email",
                "confirm_email",
                text=(
                    f"Hi {current_user.full_name},\n\n"
                    "Open this link to confirm that this is your new C.A.T.E.R. email. "
                    f"It works for {minutes} minutes and can only be used once:\n\n"
                    f"{confirm_url}\n\n"
                    "If you did not ask for this, ignore this email. Nothing will change."
                ),
                user=current_user,
                confirm_url=confirm_url,
                minutes=minutes,
            )
        except Exception:
            current_app.logger.exception("Could not send the email-change confirmation")
            flash("We could not send the confirmation email. Please try again later.", "danger")
            return render_profile(email_form=form, open_section="email")

        flash(
            f"We sent a confirmation link to {new_email}. "
            "Your email changes after you open it.",
            "info",
        )
        return redirect(url_for("profile.show_profile"))

    return render_profile(email_form=form, open_section="email")


@profile_bp.route("/confirm-email/<token>")
@login_required
def confirm_email(token):
    new_email = read_email_token(token, current_user)
    if new_email is None:
        flash("That confirmation link is invalid or has expired.", "warning")
        return redirect(url_for("profile.show_profile"))

    if User.query.filter_by(email=new_email).first():
        flash("That email now belongs to another account.", "danger")
        return redirect(url_for("profile.show_profile"))

    old_email = current_user.email
    current_user.email = new_email
    try:
        current_user.save()
    except IntegrityError:
        # Someone took the address between our check and the save (the database
        # column is UNIQUE, so it refuses). Undo and tell the user.
        db.session.rollback()
        flash("That email now belongs to another account.", "danger")
        return redirect(url_for("profile.show_profile"))

    notify(
        old_email,
        "Your C.A.T.E.R. email was changed",
        "security_notice",
        text=(
            f"Hi {current_user.full_name},\n\n"
            f"The email on your C.A.T.E.R. account was changed to {new_email}. "
            "If this was not you, contact an administrator right away."
        ),
        user=current_user,
        heading="Your email was changed",
        message=f"The email on your C.A.T.E.R. account was changed to {new_email}. "
        "If this was not you, contact an administrator right away.",
    )
    flash("Your email has been updated.", "success")
    return redirect(url_for("profile.show_profile"))


@profile_bp.route("/password", methods=["POST"])
@login_required
def update_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        current_user.set_password(form.password.data)
        current_user.save()

        notify(
            current_user.email,
            "Your C.A.T.E.R. password was changed",
            "security_notice",
            text=(
                f"Hi {current_user.full_name},\n\n"
                "The password on your C.A.T.E.R. account was just changed. "
                "If this was not you, reset it right away with 'Forgot password?' "
                "and tell an administrator."
            ),
            user=current_user,
            heading="Your password was changed",
            message="The password on your C.A.T.E.R. account was just changed. "
            "If this was not you, reset it right away with 'Forgot password?' "
            "and tell an administrator.",
        )
        flash("Your password has been changed.", "success")
        return redirect(url_for("profile.show_profile"))

    return render_profile(password_form=form, open_section="password")
