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
from sqlalchemy.orm import joinedload

from app import db
from app.decorators import admin_required
from app.forms import AssignEquipmentForm, EventCreateForm, StaffStatusForm
from app.models import Equipment, Event, EventEquipment, User

staff_bp = Blueprint("staff", __name__, url_prefix="/staff")

STATUSES = ("available", "in event")


# ---------- Helpers ----------


def build_status_form():
    """The admin's "update status" form, with the list of events to choose from."""
    form = StaffStatusForm()
    events = Event.query.order_by(Event.name).all()
    form.event_id.choices = [(0, "No event")] + [
        (e.id, f"{e.name} ({e.venue})" if e.venue else e.name) for e in events
    ]
    return form


def render_detail(member, status_form=None, open_status=False):
    """One person's page: their status, their event and the equipment of that event."""
    is_admin = current_user.role == "admin"
    event = member.current_event if member.status == "in event" else None

    if is_admin and status_form is None:
        status_form = build_status_form()
        # Start the form from what is saved. (Only on a fresh page, never after an error.)
        status_form.status.data = member.status if member.status in STATUSES else "available"
        status_form.event_id.data = member.current_event_id or 0

    return render_template(
        "staff/detail.html",
        member=member,
        event=event,
        assignments=event.equipment_assignments if event else [],
        is_admin=is_admin,
        status_form=status_form,
        open_status=open_status,
    )


# ---------- Staff directory (everyone logged in can view) ----------


@staff_bp.route("/")
@login_required
def index():
    # request.args holds the ?q=...&status=... part of the address.
    q = request.args.get("q", "").strip()[:100]
    status = request.args.get("status", "")

    everyone = User.query.all()
    counts = {
        "total": len(everyone),
        "available": sum(1 for s in everyone if s.status == "available"),
        "in event": sum(1 for s in everyone if s.status == "in event"),
    }

    # joinedload fetches each person's event in the same query, instead of one extra
    # query per person while the page is being drawn.
    query = User.query.options(joinedload(User.current_event))
    if q:
        query = query.filter(User.full_name.ilike(f"%{q}%"))
    if status in STATUSES:  # an unknown value is simply ignored
        query = query.filter(User.status == status)

    return render_template(
        "staff/index.html",
        members=query.order_by(User.full_name).all(),
        counts=counts,
        q=q,
        status=status,
    )


@staff_bp.route("/<int:user_id>")
@login_required
def detail(user_id):
    # get_or_404 shows the friendly "not found" page when the id does not exist
    member = db.get_or_404(User, user_id)
    return render_detail(member)


# ---------- Status (admin only). Name and role can no longer be changed here. ----------


@staff_bp.route("/<int:user_id>/edit", methods=["GET", "POST"])
@admin_required
def edit(user_id):
    # Kept under its old endpoint name so any old link or url_for("staff.edit") still works.
    member = db.get_or_404(User, user_id)
    if request.method == "GET":
        return redirect(url_for("staff.detail", user_id=member.id))

    form = build_status_form()
    if form.validate_on_submit():
        if form.status.data == "in event":
            if not form.event_id.data:
                form.event_id.errors = list(form.event_id.errors) + ["Choose the event they are in."]
                return render_detail(member, status_form=form, open_status=True)
            member.status = "in event"
            member.current_event_id = form.event_id.data
        else:
            member.status = "available"
            member.current_event_id = None  # available people are not in any event
        member.save()
        flash(f"{member.full_name} is now {member.status}.", "success")
        return redirect(url_for("staff.detail", user_id=member.id))

    return render_detail(member, status_form=form, open_status=True)


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
