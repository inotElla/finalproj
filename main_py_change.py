# In app/routes/main.py:
# 1) change the import line to:
#      from app.models import Equipment, EquipmentUnit, Event, User
# 2) replace the whole dashboard() function with this one.

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
    recent = Equipment.query.order_by(Equipment.created_at.desc()).limit(6).all()
    staff = User.query.order_by(User.full_name).all() if current_user.role == "admin" else []

    return render_template(
        "dashboard.html",
        stats=stats,
        events=events,
        recent=recent,
        staff=staff,
        staff_total=len(staff),
    )
