from flask import Blueprint, flash, redirect, render_template, url_for

from app.forms import RegistrationForm
from app.models import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
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
        return redirect(url_for("main.index"))

    return render_template("register.html", form=form)