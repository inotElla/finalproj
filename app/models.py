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


class User(UserMixin, BaseModel):
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="staff")
    profile_photo = db.Column(db.String(255))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


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


class Event(BaseModel):
    client_name = db.Column(db.String(100), nullable=False)
    event_date = db.Column(db.Date, nullable=False)
    end_time = db.Column(db.DateTime)
    location = db.Column(db.String(200))
    status = db.Column(db.String(20), default="upcoming")

    checkouts = db.relationship("Checkout", back_populates="event")


class Checkout(BaseModel):
    event_id = db.Column(db.Integer, db.ForeignKey("event.id"), nullable=False)
    equipment_id = db.Column(db.Integer, db.ForeignKey("equipment.id"), nullable=False)
    unit_id = db.Column(db.Integer, db.ForeignKey("equipment_unit.id"))

    status = db.Column(db.String(20), nullable=False, default="planned")
    quantity_out = db.Column(db.Integer, nullable=False, default=1)
    quantity_returned = db.Column(db.Integer, default=0)
    quantity_damaged = db.Column(db.Integer, default=0)
    quantity_missing = db.Column(db.Integer, default=0)

    date_out = db.Column(db.DateTime)
    date_returned = db.Column(db.DateTime)

    event = db.relationship("Event", back_populates="checkouts")
    equipment = db.relationship("Equipment")
    unit = db.relationship("EquipmentUnit")


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))