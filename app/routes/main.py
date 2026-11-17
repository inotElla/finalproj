from datetime import datetime, time, timedelta, timezone

from flask import Blueprint, jsonify, render_template
from flask_login import current_user, login_required

from app.forms import LoginForm, RegistrationForm
from app.models import Equipment, EquipmentUnit, Event, User

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
    # The home page holds the Log in / Register pop-ups, so it needs both (empty) forms.
    return render_template(
        "index.html",
        login_form=LoginForm(formdata=None),
        register_form=RegistrationForm(formdata=None),
        open_modal=None,
    )


@main_bp.route("/api/health")
def health():
    return jsonify({"status": "ok", "app": "C.A.T.E.R"})


@main_bp.route("/dashboard")
@login_required
def dashboard():
    # Events that are not finished. "ongoing" sorts before "upcoming", then by date.
    events = (
        Event.query.filter(Event.status != "completed")
        .order_by(Event.status.asc(), Event.event_date.asc())
        .limit(5)
        .all()
    )
    stats = {
        "equipment": Equipment.query.count(),
        "items_out": EquipmentUnit.query.filter_by(status="out").count(),
        "events": Event.query.filter(Event.status != "completed").count(),
    }
    # Pick-up alerts: an event is "over" once its end time has passed (no end time =
    # the end of that day). If it is not completed and still has equipment nobody has
    # marked as returned, it needs a pick-up.
    now = datetime.now(PH_TZ).replace(tzinfo=None)  # Philippine time, like the dates users type
    candidates = (
        Event.query.filter(Event.status != "completed", Event.event_date.isnot(None), Event.event_date <= now)
        .order_by(Event.event_date.asc())
        .all()
    )
    pickups = []
    for event in candidates:
        ended_at = datetime.combine(event.event_date.date(), event.end_time or time(23, 59, 59))
        if ended_at > now:
            continue  # still running
        # Count of items (by quantity) on lines with no return recorded yet.
        waiting = sum(line.quantity or 0 for line in event.equipment_assignments if not line.is_returned)
        if waiting:
            hours_late = int((now - ended_at).total_seconds() // 3600)
            pickups.append({"event": event, "waiting": waiting, "hours_late": hours_late, "ended_at": ended_at})

    recent = Equipment.query.order_by(Equipment.created_at.desc()).limit(6).all()
    staff = User.query.order_by(User.full_name).all() if current_user.role == "admin" else []

    return render_template(
        "dashboard.html",
        stats=stats,
        events=events,
        recent=recent,
        pickups=pickups,
        staff=staff,
        staff_total=len(staff),
    )

