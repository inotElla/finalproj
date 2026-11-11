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
    role = db.Column(db.String(50), nullable=False)
    
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
