from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, render_template
from flask_login import current_user, login_required

from app.models import Equipment, EquipmentUnit, User

main_bp = Blueprint("main", __name__)

PH_TZ = timezone(timedelta(hours=8))


@main_bp.app_template_filter("localtime")
def localtime(value, fmt="%b %d, %Y %I:%M %p"):
    if value is None:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(PH_TZ).strftime(fmt)


@main_bp.route("/")
def index():
    return render_template("index.html")


@main_bp.route("/api/health")
def health():
    return jsonify({"status": "ok", "app": "C.A.T.E.R"})


@main_bp.route("/dashboard")
@login_required
def dashboard():
    stats = {
        "equipment": Equipment.query.count(),
        "items_out": EquipmentUnit.query.filter_by(status="out").count(),
    }
    recent = Equipment.query.order_by(Equipment.created_at.desc()).limit(6).all()
    staff = User.query.order_by(User.full_name).all() if current_user.role == "admin" else []

    return render_template(
        "dashboard.html",
        stats=stats,
        recent=recent,
        staff=staff,
        staff_total=len(staff),
    )
