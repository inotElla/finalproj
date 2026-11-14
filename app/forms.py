from flask_login import current_user
from flask_wtf import FlaskForm
from wtforms import BooleanField, EmailField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError

from app.models import User


def letter_and_number(form, field):
    pw = field.data or ""
    if not (any(c.isalpha() for c in pw) and any(c.isdigit() for c in pw)):
        raise ValidationError("Password must contain a letter and a number.")


class RegistrationForm(FlaskForm):
    full_name = StringField(
        "Full name", validators=[DataRequired(), Length(min=2, max=100)]
    )
    email = EmailField(
        "Email", validators=[DataRequired(), Email(), Length(max=120)]
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired(), Length(min=8, max=128), letter_and_number],
    )
    confirm_password = PasswordField(
        "Confirm password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")],
    )
    submit = SubmitField("Create account")

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.strip().lower()).first():
            raise ValidationError("Email is already registered.")


class LoginForm(FlaskForm):
    email = EmailField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Remember me")
    submit = SubmitField("Log in")


class PasswordResetRequestForm(FlaskForm):
    email = EmailField(
        "Email", validators=[DataRequired(), Email(), Length(max=120)]
    )
    submit = SubmitField("Send reset link")


class ResetPasswordForm(FlaskForm):
    password = PasswordField(
        "New password",
        validators=[DataRequired(), Length(min=8, max=128), letter_and_number],
    )
    confirm_password = PasswordField(
        "Confirm new password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")],
    )
    submit = SubmitField("Reset password")


# ---------- Profile page (three separate forms) ----------
# Every field on the profile page needs a different name, because all three forms
# sit on ONE page and an HTML id must be unique. "password" and "confirm_password"
# are kept on purpose: app.js uses those two ids to check that the passwords match.


class ProfileNameForm(FlaskForm):
    full_name = StringField(
        "Full name", validators=[DataRequired(), Length(min=2, max=100)]
    )
    save_name = SubmitField("Save name")


class ChangeEmailForm(FlaskForm):
    new_email = EmailField(
        "New email", validators=[DataRequired(), Email(), Length(max=120)]
    )
    email_password = PasswordField("Current password", validators=[DataRequired()])
    save_email = SubmitField("Send confirmation link")

    def validate_new_email(self, field):
        new_email = field.data.strip().lower()
        if new_email == current_user.email.lower():
            raise ValidationError("That is already your email.")
        if User.query.filter_by(email=new_email).first():
            raise ValidationError("Email is already registered.")

    def validate_email_password(self, field):
        if not current_user.check_password(field.data):
            raise ValidationError("Current password is incorrect.")


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField("Current password", validators=[DataRequired()])
    password = PasswordField(
        "New password",
        validators=[DataRequired(), Length(min=8, max=128), letter_and_number],
    )
    confirm_password = PasswordField(
        "Confirm new password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")],
    )
    save_password = SubmitField("Change password")

    def validate_current_password(self, field):
        if not current_user.check_password(field.data):
            raise ValidationError("Current password is incorrect.")

    def validate_password(self, field):
        if current_user.check_password(field.data):
            raise ValidationError("Your new password must be different from the current one.")
