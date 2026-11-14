from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash
from app import db, login_manager


def utc_now():
    return datetime.now(timezone.utc)


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

    units = db.relationship("EquipmentUnit", back_populates="equipment")


class EquipmentUnit(BaseModel):
    equipment_id = db.Column(db.Integer, db.ForeignKey("equipment.id"), nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=False)
    condition = db.Column(db.String(30), default="good")
    status = db.Column(db.String(30), default="available")

    equipment = db.relationship("Equipment", back_populates="units")


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))