from functools import wraps
from flask import (
    Blueprint,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from app import db
from app.forms import AssignEquipmentForm, EventCreateForm, StaffEditForm
from app.models import Equipment, Event, EventEquipment, User

staff_bp = Blueprint("staff", __name__, url_prefix="/staff")


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "admin":
            flash("Permission denied. Only administrators can perform this action.", "danger")
            return redirect(url_for("staff.index"))
        return f(*args, **kwargs)
    return decorated_function


# 1. Staff Directory (All logged-in staff can view)
@staff_bp.route("/")
@login_required
def index():
    staff_members = User.query.order_by(User.full_name).all()
    events = Event.query.order_by(Event.name).all()

    total_staff = len(staff_members)
    available_count = sum(1 for s in staff_members if s.status == "available")
    in_event_count = sum(1 for s in staff_members if s.status == "in event")

    return render_template(
        "staff/index.html",
        staff_members=staff_members,
        events=events,
        total_staff=total_staff,
        available_count=available_count,
        in_event_count=in_event_count,
        is_admin=(current_user.role == "admin"),
    )


# 2. Staff Details View (All staff can view, non-admins see read-only view)
@staff_bp.route("/<int:user_id>")
@login_required
def detail(user_id):
    staff_member = db.session.get(User, user_id)
    if not staff_member:
        flash("Staff member not found.", "warning")
        return redirect(url_for("staff.index"))

    return render_template(
        "staff/detail.html",
        staff=staff_member,
        current_event=staff_member.current_event,
        is_admin=(current_user.role == "admin"),
    )


# 3. Staff Edit & Event Assignment (Admin ONLY)
@staff_bp.route("/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit(user_id):
    staff_member = db.session.get(User, user_id)
    if not staff_member:
        flash("Staff member not found.", "warning")
        return redirect(url_for("staff.index"))

    form = StaffEditForm(obj=staff_member)

    active_events = Event.query.order_by(Event.name).all()
    form.event_id.choices = [(0, "-- None (Available) --")] + [
        (e.id, f"{e.name}{' (' + e.venue + ')' if e.venue else ''}") for e in active_events
    ]

    if request.method == "GET":
        form.event_id.data = staff_member.current_event_id or 0

    if form.validate_on_submit():
        staff_member.full_name = " ".join(form.full_name.data.split())
        staff_member.role = form.role.data
        staff_member.status = form.status.data

        selected_event_id = form.event_id.data
        if staff_member.status == "in event" and selected_event_id and selected_event_id > 0:
            staff_member.current_event_id = selected_event_id
        else:
            staff_member.status = "available"
            staff_member.current_event_id = None

        staff_member.save()
        flash(f"Staff details for {staff_member.full_name} have been updated.", "success")
        return redirect(url_for("staff.detail", user_id=staff_member.id))

    return render_template(
        "staff/edit.html",
        form=form,
        staff=staff_member,
        events=active_events,
    )


# 4. JSON API: Fetch equipment assigned to an event (used by modal)
@staff_bp.route("/api/event/<int:event_id>/equipment")
@login_required
def event_equipment_api(event_id):
    event = db.session.get(Event, event_id)
    if not event:
        return jsonify({"error": "Event not found"}), 404

    equipments = []
    for assignment in event.equipment_assignments:
        eq = assignment.equipment
        unit = assignment.unit
        equipments.append({
            "id": assignment.id,
            "name": eq.name if eq else "Unknown item",
            "category": eq.category if eq and eq.category else "General",
            "tracking_type": eq.tracking_type if eq else "bulk",
            "unit_code": unit.code if unit else None,
            "condition": unit.condition if unit else "good",
            "quantity": assignment.quantity,
            "notes": assignment.notes or "",
        })

    staff_list = [
        {"id": s.id, "name": s.full_name, "role": s.role, "initials": s.initials}
        for s in event.staff_members
    ]

    return jsonify({
        "event_id": event.id,
        "name": event.name,
        "venue": event.venue or "No venue specified",
        "status": event.status.capitalize(),
        "staff_members": staff_list,
        "equipments": equipments,
        "total_equipment_count": sum(e["quantity"] for e in equipments),
    })


# 5. Full Event & Equipment Details View
@staff_bp.route("/events/<int:event_id>")
@login_required
def event_detail(event_id):
    event = db.session.get(Event, event_id)
    if not event:
        flash("Event not found.", "warning")
        return redirect(url_for("staff.index"))

    assign_form = AssignEquipmentForm() if current_user.role == "admin" else None
    if assign_form:
        equipments = Equipment.query.order_by(Equipment.name).all()
        assign_form.equipment_id.choices = [(e.id, f"{e.name} ({e.category or 'General'})") for e in equipments]

    return render_template(
        "staff/event_detail.html",
        event=event,
        assign_form=assign_form,
        is_admin=(current_user.role == "admin"),
    )


# 6. Admin Event Creation
@staff_bp.route("/events/new", methods=["GET", "POST"])
@login_required
@admin_required
def create_event():
    form = EventCreateForm()
    if form.validate_on_submit():
        event = Event(
            name=form.name.data.strip(),
            venue=form.venue.data.strip() if form.venue.data else None,
            status=form.status.data,
        )
        event.save()
        flash(f"Event '{event.name}' has been created successfully.", "success")
        return redirect(url_for("staff.index"))

    return render_template("staff/event_form.html", form=form)


# 7. Admin Assign Equipment to Event
@staff_bp.route("/events/<int:event_id>/equipment/assign", methods=["POST"])
@login_required
@admin_required
def assign_equipment(event_id):
    event = db.session.get(Event, event_id)
    if not event:
        flash("Event not found.", "warning")
        return redirect(url_for("staff.index"))

    form = AssignEquipmentForm()
    equipments = Equipment.query.order_by(Equipment.name).all()
    form.equipment_id.choices = [(e.id, e.name) for e in equipments]

    if form.validate_on_submit():
        eq = db.session.get(Equipment, form.equipment_id.data)
        assignment = EventEquipment(
            event_id=event.id,
            equipment_id=eq.id,
            quantity=form.quantity.data,
            notes=form.notes.data.strip() if form.notes.data else None,
        )
        assignment.save()
        flash(f"Assigned {form.quantity.data}x {eq.name} to {event.name}.", "success")

    return redirect(url_for("staff.event_detail", event_id=event.id))