from urllib.parse import urlparse

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.forms import LoginForm, RegistrationForm
from app.models import User

auth_bp = Blueprint("auth", __name__)


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