from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, render_template
from flask_login import login_required
from sqlalchemy import func

from app import db
from app.models import Checkout, Equipment, Event

main_bp = Blueprint("main", __name__)

# The Philippines has no daylight saving time, so a fixed UTC+8 offset is enough.
PH_TZ = timezone(timedelta(hours=8))


@main_bp.app_template_filter("localtime")
def localtime(value, fmt="%b %d, %Y %I:%M %p"):
    """Show a UTC timestamp from the database in Philippine time."""
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
    now = datetime.now()

    items_out = (
        db.session.query(
            func.coalesce(
                func.sum(
                    Checkout.quantity_out
                    - Checkout.quantity_returned
                    - Checkout.quantity_damaged
                    - Checkout.quantity_missing
                ),
                0,
            )
        )
        .filter(Checkout.status == "out")
        .scalar()
    )

    # Events whose end time has passed but that are not closed out yet.
    overdue = (
        Event.query.filter(Event.end_time < now, Event.status != "completed")
        .order_by(Event.end_time)
        .all()
    )

    stats = {
        "equipment": Equipment.query.count(),
        "upcoming": Event.query.filter(Event.status == "upcoming").count(),
        "items_out": int(items_out or 0),
        "overdue": len(overdue),
    }

    events = (
        Event.query.filter(Event.status != "completed")
        .order_by(Event.event_date)
        .limit(5)
        .all()
    )
    recent = Checkout.query.order_by(Checkout.created_at.desc()).limit(6).all()

    return render_template(
        "dashboard.html", stats=stats, overdue=overdue, events=events, recent=recent
    )
