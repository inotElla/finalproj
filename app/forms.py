from flask_login import current_user
from flask_wtf import FlaskForm
from sqlalchemy import func
from wtforms import (
    BooleanField,
    DateField,
    EmailField,
    IntegerField,
    PasswordField,
    SelectField,
    StringField,
    SubmitField,
    TimeField,
)
from wtforms.validators import (
    DataRequired,
    Email,
    EqualTo,
    InputRequired,
    Length,
    NumberRange,
    Optional,
    ValidationError,
)

from app.models import (
    CATEGORIES,
    EQUIPMENT_NAME_MAX,
    EVENT_STATUSES,
    MAX_UNITS_AT_ONCE,
    UNIT_CONDITIONS,
    UNIT_STATUSES,
    Equipment,
    User,
)


def strip(value):
    """A WTForms filter: remove spaces at both ends of what was typed.
    (None, for a box that was not sent at all, is left alone.)"""
    return value.strip() if isinstance(value, str) else value


def real_name(form, field):
    """A person's name: letters, spaces, apostrophes, hyphens and periods only."""
    name = field.data or ""
    if not any(c.isalpha() for c in name):
        raise ValidationError("Name must contain letters.")
    if any(not (c.isalpha() or c in " .'-") for c in name):
        raise ValidationError("Name can only have letters, spaces, apostrophes, hyphens and periods.")


def letter_and_number(form, field):
    """Shared rule: the password needs at least one letter and one digit."""
    pw = field.data or ""
    if not (any(c.isalpha() for c in pw) and any(c.isdigit() for c in pw)):
        raise ValidationError("Password must contain a letter and a number.")


class RegistrationForm(FlaskForm):
    full_name = StringField(
        "Full name", validators=[DataRequired(), Length(min=2, max=100), real_name], filters=[strip]
    )
    email = EmailField(
        "Email", validators=[DataRequired(), Email(), Length(max=120)], filters=[strip]
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
    email = EmailField("Email", validators=[DataRequired(), Email()], filters=[strip])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Remember me")
    submit = SubmitField("Log in")


class PasswordResetRequestForm(FlaskForm):
    email = EmailField(
        "Email", validators=[DataRequired(), Email(), Length(max=120)], filters=[strip]
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
        "Full name", validators=[DataRequired(), Length(min=2, max=100), real_name], filters=[strip]
    )
    save_name = SubmitField("Save name")


class ChangeEmailForm(FlaskForm):
    new_email = EmailField(
        "New email", validators=[DataRequired(), Email(), Length(max=120)], filters=[strip]
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


# ---------- Staff & Event Management Forms ----------

class StaffStatusForm(FlaskForm):
    # Admin only. Name and role are no longer editable, so they are not in this form.
    status = SelectField(
        "Status",
        choices=[("available", "Available"), ("in event", "In event")],
        validators=[DataRequired()],
    )
    # coerce=int turns the chosen text ("3") into a number (3). 0 means "no event".
    event_id = SelectField("Event", coerce=int, validators=[Optional()])
    save_status = SubmitField("Save status")


class EventForm(FlaskForm):
    name = StringField(
        "Event name", validators=[DataRequired(), Length(min=2, max=150)], filters=[strip]
    )
    venue = StringField(
        "Venue / location", validators=[Optional(), Length(max=200)], filters=[strip]
    )
    # DateField draws a date picker. Optional(): the date can be left empty.
    event_date = DateField("Date", validators=[Optional()])
    # TimeField draws a time picker. Once this time passes, unreturned items appear in Pick-up alerts.
    end_time = TimeField("Ends at", validators=[Optional()])
    status = SelectField(
        "Status",
        choices=[(s, s.capitalize()) for s in EVENT_STATUSES],
        default="upcoming",
    )
    save = SubmitField("Save event")

    def validate_end_time(self, field):
        if field.data and not self.event_date.data:
            raise ValidationError("Pick the event date first, then the time it ends.")


class AssignEquipmentForm(FlaskForm):
    equipment_id = SelectField("Equipment", coerce=int, validators=[DataRequired()])
    quantity = IntegerField(
        "Quantity", default=1, validators=[DataRequired(), NumberRange(min=1, max=100000)]
    )
    notes = StringField("Notes", validators=[Optional(), Length(max=200)], filters=[strip])
    assign = SubmitField("Assign equipment")


class AssignStaffForm(FlaskForm):
    user_id = SelectField("Staff member", coerce=int, validators=[DataRequired()])
    add_staff = SubmitField("Add to event")


class ReturnForm(FlaskForm):
    # InputRequired (not DataRequired) because 0 is a real answer: "none came back".
    returned_quantity = IntegerField(
        "Returned", validators=[InputRequired(), NumberRange(min=0, max=100000)]
    )
    issue_note = StringField("Note", validators=[Optional(), Length(max=200)], filters=[strip])
    save_return = SubmitField("Save return")


# ---------- Equipment ----------


class EquipmentForm(FlaskForm):
    name = StringField(
        "Name",
        validators=[DataRequired(), Length(min=2, max=EQUIPMENT_NAME_MAX)],
        filters=[strip],
    )
    category = SelectField("Category", choices=[(c, c) for c in CATEGORIES])
    tracking_type = SelectField(
        "How do you track it?",
        choices=[("bulk", "By quantity"), ("individual", "One by one")],
    )
    quantity_total = IntegerField(
        "Quantity", default=1, validators=[NumberRange(min=0, max=100000)]
    )
    save = SubmitField("Save equipment")

    def __init__(self, *args, equipment=None, **kwargs):
        # The equipment being edited (None when adding a new one). The checks
        # below need it so an item is not compared against itself.
        self.equipment = equipment
        super().__init__(*args, **kwargs)

    def validate_name(self, field):
        name = " ".join(field.data.split())
        query = Equipment.query.filter(func.lower(Equipment.name) == name.lower())
        if self.equipment is not None:
            query = query.filter(Equipment.id != self.equipment.id)
        if query.first():
            raise ValidationError("You already have equipment with that name.")

    def validate_tracking_type(self, field):
        if self.equipment is not None and field.data == "bulk" and self.equipment.units:
            raise ValidationError(
                "This item has units. Delete them first, or keep it tracked one by one."
            )

    def validate_quantity_total(self, field):
        # For "one by one", the quantity is how many separate units get created.
        if (
            self.tracking_type.data == "individual"
            and field.data is not None
            and field.data > MAX_UNITS_AT_ONCE
        ):
            raise ValidationError(f"You can create up to {MAX_UNITS_AT_ONCE} units at a time.")

        # Editing a by-quantity item: the stock cannot go below what events already hold.
        if (
            self.equipment is not None
            and self.tracking_type.data == "bulk"
            and field.data is not None
        ):
            held = self.equipment.assigned_quantity
            if field.data < held:
                raise ValidationError(
                    f"{held} are promised to events, so the quantity cannot be lower than that."
                )


class AddUnitsForm(FlaskForm):
    count = IntegerField(
        "How many?",
        default=1,
        validators=[DataRequired(), NumberRange(min=1, max=MAX_UNITS_AT_ONCE)],
    )
    condition = SelectField(
        "Condition", choices=[(c, c.capitalize()) for c in UNIT_CONDITIONS]
    )
    add_units = SubmitField("Add units")


class UnitForm(FlaskForm):
    # A unit's name is made from its equipment name, so only these can be changed.
    condition = SelectField(
        "Condition", choices=[(c, c.capitalize()) for c in UNIT_CONDITIONS]
    )
    status = SelectField("Status", choices=[(s, s.capitalize()) for s in UNIT_STATUSES])
    save = SubmitField("Save unit")


