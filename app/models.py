import re
from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash
from app import db, login_manager

# Fixed lists used by the forms and the templates. Keeping them in one place means
# a new category or status is added here only.
CATEGORIES = [
    "Tableware",
    "Glassware",
    "Cookware",
    "Serving ware",
    "Linens",
    "Furniture",
    "Appliances",
    "Other",
]
UNIT_CONDITIONS = ["good", "fair", "needs repair", "damaged"]
UNIT_STATUSES = ["available", "out", "maintenance", "lost"]

# A unit is named after its equipment: "Chafing Dish #1", "Chafing Dish #2", ...
# The equipment name is limited to 40 characters (see forms.py) so the unit name
# always fits the 50-character column.
EQUIPMENT_NAME_MAX = 40
MAX_UNITS_AT_ONCE = 500


def utc_now():
    return datetime.now(timezone.utc)


def unit_label(equipment_name, number):
    return f"{equipment_name} #{number}"


class BaseModel(db.Model):
    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    def save(self):
        db.session.add(self)
        db.session.commit()
        return self

    def delete(self):
        db.session.delete(self)
        db.session.commit()


class User(BaseModel, UserMixin):
    __tablename__ = 'user'
    
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False, default="staff")  # 'admin' or 'staff'
    
    # Staff status: strictly "available" or "in event"
    status = db.Column(db.String(30), nullable=False, default="available")
    
    # Active event assignment
    current_event_id = db.Column(
        db.Integer, db.ForeignKey("event.id", ondelete="SET NULL"), nullable=True
    )
    
    current_event = db.relationship(
        "Event",
        back_populates="staff_members",
        foreign_keys=[current_event_id],
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def initials(self):
        parts = self.full_name.split()
        if not parts:
            return "?"
        if len(parts) == 1:
            return parts[0][:2].upper()
        return (parts[0][0] + parts[-1][0]).upper()

    @property
    def is_in_event(self):
        return self.status == "in event" and self.current_event is not None


class Event(BaseModel):
    __tablename__ = 'event'

    name = db.Column(db.String(150), nullable=False)
    venue = db.Column(db.String(200), nullable=True)
    event_date = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(30), default="ongoing")  # "upcoming", "ongoing", "completed"

    staff_members = db.relationship(
        "User",
        back_populates="current_event",
        foreign_keys="User.current_event_id",
    )

    equipment_assignments = db.relationship(
        "EventEquipment",
        back_populates="event",
        cascade="all, delete-orphan",
    )

    @property
    def total_equipment_count(self):
        return sum(item.quantity for item in self.equipment_assignments)


class EventEquipment(BaseModel):
    __tablename__ = 'event_equipment'

    event_id = db.Column(db.Integer, db.ForeignKey("event.id", ondelete="CASCADE"), nullable=False)
    equipment_id = db.Column(db.Integer, db.ForeignKey("equipment.id", ondelete="CASCADE"), nullable=False)
    unit_id = db.Column(db.Integer, db.ForeignKey("equipment_unit.id", ondelete="SET NULL"), nullable=True)
    quantity = db.Column(db.Integer, default=1)
    notes = db.Column(db.String(200), nullable=True)

    event = db.relationship("Event", back_populates="equipment_assignments")
    equipment = db.relationship("Equipment")
    unit = db.relationship("EquipmentUnit")


class Equipment(BaseModel):
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50))
    tracking_type = db.Column(db.String(20), nullable=False, default="bulk")
    quantity_total = db.Column(db.Integer, default=0)

    # cascade="all, delete-orphan": deleting a piece of equipment also deletes its
    # units, so no unit is ever left pointing at something that no longer exists.
    units = db.relationship(
        "EquipmentUnit", back_populates="equipment", cascade="all, delete-orphan"
    )

    @property
    def stock(self):
        """How many we own: the typed quantity, or the number of units."""
        if self.tracking_type == "bulk":
            return self.quantity_total or 0
        return len(self.units)

    @property
    def units_available(self):
        return sum(1 for unit in self.units if unit.status == "available")

    @property
    def assignment_count(self):
        """How many event assignments use this equipment."""
        return EventEquipment.query.filter_by(equipment_id=self.id).count()

    def next_unit_number(self):
        # Look at the numbers already used ("... #3") and continue after the highest,
        # so a deleted unit's number is never handed out again.
        numbers = []
        for unit in self.units:
            match = re.search(r"#(\d+)$", unit.code)
            if match:
                numbers.append(int(match.group(1)))
        return max(numbers, default=0) + 1

    def add_units(self, count, condition="good"):
        """Create `count` new units named after this equipment, and save them."""
        start = self.next_unit_number()
        for offset in range(count):
            db.session.add(
                EquipmentUnit(
                    equipment_id=self.id,
                    code=unit_label(self.name, start + offset),
                    condition=condition,
                    status="available",
                )
            )
        db.session.commit()

    def refresh_unit_labels(self):
        """After a rename, give every unit the new name and keep its number."""
        for unit in self.units:
            match = re.search(r"#(\d+)$", unit.code)
            if match:
                unit.code = unit_label(self.name, int(match.group(1)))
        db.session.commit()

    def delete(self):
        # Remove this equipment from any event first, so no event is left pointing
        # at something that is gone (the database may or may not do this by itself).
        EventEquipment.query.filter_by(equipment_id=self.id).delete()
        super().delete()


class EquipmentUnit(BaseModel):
    equipment_id = db.Column(db.Integer, db.ForeignKey("equipment.id"), nullable=False)
    # The unit's name, made from the equipment name plus a number ("Chafing Dish #2").
    # It is generated, never typed. The column keeps its old name, "code".
    code = db.Column(db.String(50), unique=True, nullable=False)
    condition = db.Column(db.String(30), default="good")
    status = db.Column(db.String(30), default="available")

    equipment = db.relationship("Equipment", back_populates="units")

    def delete(self):
        # Events that used this exact unit keep their line, just without the unit.
        EventEquipment.query.filter_by(unit_id=self.id).update({"unit_id": None})
        super().delete()


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
