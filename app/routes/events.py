from datetime import datetime, time

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.activity import log_activity
from app.decorators import admin_required
from app.forms import AssignEquipmentForm, AssignStaffForm, EventForm
from app.models import (
    EVENT_STATUSES,
    Equipment,
    EquipmentUnit,
    Event,
    EventEquipment,
    User,
)

events_bp = Blueprint("events", __name__, url_prefix="/events")

PER_PAGE = 10


def clean(text):
    # " ".join(text.split()) collapses extra spaces: "  Garden   Wedding " -> "Garden Wedding"
    return " ".join(text.split())


def to_datetime(day):
    # The date picker gives a date (2026-11-20). The column stores a datetime, so add midnight.
    return datetime.combine(day, time.min) if day else None


# ---------- Forms that need a list of choices ----------


def equipment_form_for(fresh):
    """The "assign equipment" form. fresh=True starts empty; fresh=False reads what was posted."""
    # formdata=None means "do not read request.form".
    form = AssignEquipmentForm(formdata=None) if fresh else AssignEquipmentForm()
    items = Equipment.query.order_by(Equipment.name).all()
    # Only items that still have something free are offered, with how many are free.
    form.equipment_id.choices = [
        (e.id, f"{e.name} ({e.category or 'General'}) - {e.free_quantity} free")
        for e in items
        if e.free_quantity > 0
    ]
    return form


def staff_form_for(fresh):
    form = AssignStaffForm(formdata=None) if fresh else AssignStaffForm()
    people = User.query.filter_by(status="available").order_by(User.full_name).all()
    form.user_id.choices = [(p.id, p.full_name) for p in people]
    return form


# ---------- Page builders ----------


def render_list(add_form=None, open_add=False):
    q = request.args.get("q", "").strip()[:100]
    status = request.args.get("status", "")
    page = request.args.get("page", 1, type=int)

    query = Event.query
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Event.name.ilike(like), Event.venue.ilike(like)))
    if status in EVENT_STATUSES:  # an unknown value is simply ignored
        query = query.filter(Event.status == status)

    pagination = query.order_by(Event.event_date.desc(), Event.id.desc()).paginate(
        page=page, per_page=PER_PAGE, error_out=False
    )

    is_admin = current_user.role == "admin"
    if is_admin and add_form is None:
        add_form = EventForm(formdata=None)

    return render_template(
        "events/event_list.html",
        pagination=pagination,
        q=q,
        status=status,
        statuses=EVENT_STATUSES,
        add_form=add_form,
        open_add=open_add,
        is_admin=is_admin,
    )


def render_detail(
    event, equipment_form=None, staff_form=None, open_equipment=False, open_staff=False
):
    is_admin = current_user.role == "admin"
    # Nothing can be added to an event that is over.
    can_assign = is_admin and event.status != "completed"

    if can_assign:
        if equipment_form is None:
            equipment_form = equipment_form_for(fresh=True)
        if staff_form is None:
            staff_form = staff_form_for(fresh=True)

    return render_template(
        "events/event_detail.html",
        event=event,
        is_admin=is_admin,
        can_assign=can_assign,
        equipment_form=equipment_form,
        staff_form=staff_form,
        open_equipment=open_equipment,
        open_staff=open_staff,
    )


# ---------- Events: list, add, view, edit, delete ----------


@events_bp.route("/")
@login_required
def list_events():
    return render_list()


@events_bp.route("/new", methods=["GET", "POST"])
@admin_required
def create_event():
    if request.method == "GET":
        return redirect(url_for("events.list_events"))

    form = EventForm()
    if form.validate_on_submit():
        event = Event(
            name=clean(form.name.data),
            venue=clean(form.venue.data) if form.venue.data else None,
            event_date=to_datetime(form.event_date.data),
            status=form.status.data,
        )
        event.save()
        flash(f'Event "{event.name}" was created.', "success")
        log_activity("created", "event", f'created event "{event.name}"')
        return redirect(url_for("events.view_event", event_id=event.id))

    return render_list(add_form=form, open_add=True)


@events_bp.route("/<int:event_id>")
@login_required
def view_event(event_id):
    event = db.get_or_404(Event, event_id)
    return render_detail(event)


@events_bp.route("/<int:event_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_event(event_id):
    event = db.get_or_404(Event, event_id)
    form = EventForm(obj=event)

    if form.validate_on_submit():
        was_completed = event.status == "completed"
        event.name = clean(form.name.data)
        event.venue = clean(form.venue.data) if form.venue.data else None
        event.event_date = to_datetime(form.event_date.data)

        finishing = form.status.data == "completed" and not was_completed
        if finishing:
            # Finishing an event is the "retrieval" step: units come back, staff are free.
            event.release()
        event.status = form.status.data
        event.save()

        if finishing:
            flash("Event completed. Its units are available again and its staff are free.", "success")
            log_activity("completed", "event", f'completed event "{event.name}"')
        else:
            flash("Event updated.", "success")
            log_activity("updated", "event", f'updated event "{event.name}"')
        return redirect(url_for("events.view_event", event_id=event.id))

    return render_template("events/event_form.html", form=form, event=event)


@events_bp.route("/<int:event_id>/delete", methods=["POST"])
@admin_required
def delete_event(event_id):
    event = db.get_or_404(Event, event_id)
    name = event.name
    event.delete()  # gives units and staff back first (see models.py)
    flash(f'Event "{name}" was deleted.', "success")
    log_activity("deleted", "event", f'deleted event "{name}"')
    return redirect(url_for("events.list_events"))


# ---------- Equipment on an event (admin only) ----------


def assign_item(event, equipment, quantity, notes):
    """Put `quantity` of an item on the event, then save."""
    if equipment.tracking_type == "individual":
        # One-by-one items: take that many available units. Each gets its own line
        # and becomes "out", so nobody else can be given the same unit.
        units = (
            EquipmentUnit.query.filter_by(equipment_id=equipment.id, status="available")
            .order_by(EquipmentUnit.id)
            .limit(quantity)
            .all()
        )
        for unit in units:
            unit.status = "out"
            db.session.add(
                EventEquipment(
                    event_id=event.id,
                    equipment_id=equipment.id,
                    unit_id=unit.id,
                    quantity=1,
                    notes=notes,
                )
            )
    else:
        # By-quantity items: add to the existing line instead of making a second one.
        # Only an untouched line (not packed, not returned) is added to. Otherwise the
        # new items get their own line, so the checklist stays correct.
        line = EventEquipment.query.filter(
            EventEquipment.event_id == event.id,
            EventEquipment.equipment_id == equipment.id,
            EventEquipment.packed.is_(False),
            EventEquipment.returned_quantity.is_(None),
        ).first()
        if line:
            line.quantity = (line.quantity or 0) + quantity
            if notes:
                line.notes = notes
        else:
            db.session.add(
                EventEquipment(
                    event_id=event.id,
                    equipment_id=equipment.id,
                    quantity=quantity,
                    notes=notes,
                )
            )
    db.session.commit()


@events_bp.route("/<int:event_id>/equipment", methods=["POST"])
@admin_required
def assign_equipment(event_id):
    event = db.get_or_404(Event, event_id)
    if event.status == "completed":
        flash("This event is completed, so equipment can no longer be added.", "warning")
        return redirect(url_for("events.view_event", event_id=event.id))

    form = equipment_form_for(fresh=False)
    if form.validate_on_submit():
        equipment = db.session.get(Equipment, form.equipment_id.data)
        quantity = form.quantity.data
        free = equipment.free_quantity

        if quantity > free:
            # Do not promise more than we own that is not already out.
            form.quantity.errors = list(form.quantity.errors) + [f"Only {free} available."]
        else:
            notes = clean(form.notes.data) if form.notes.data else None
            try:
                assign_item(event, equipment, quantity, notes)
            except SQLAlchemyError:
                db.session.rollback()
                current_app.logger.exception("Could not assign equipment")
                flash("Could not assign the equipment. Please try again.", "danger")
                return render_detail(event, equipment_form=form, open_equipment=True)
            flash(f"Assigned {quantity} x {equipment.name} to this event.", "success")
            log_activity("assigned", "event", f'assigned {quantity} x {equipment.name} to "{event.name}"')
            return redirect(url_for("events.view_event", event_id=event.id))

    return render_detail(event, equipment_form=form, open_equipment=True)


@events_bp.route("/<int:event_id>/equipment/<int:assignment_id>/remove", methods=["POST"])
@admin_required
def remove_equipment(event_id, assignment_id):
    line = db.get_or_404(EventEquipment, assignment_id)
    if line.event_id != event_id:  # the line belongs to some other event
        abort(404)
    name = line.equipment.name if line.equipment else "Item"
    event_name = line.event.name if line.event else "an event"
    line.delete()  # a one-by-one unit becomes available again (see models.py)
    flash(f"{name} was removed from this event.", "success")
    log_activity("removed", "event", f'removed {name} from "{event_name}"')
    return redirect(url_for("events.view_event", event_id=event_id))


# ---------- Staff on an event (admin only) ----------


@events_bp.route("/<int:event_id>/staff", methods=["POST"])
@admin_required
def assign_staff(event_id):
    event = db.get_or_404(Event, event_id)
    if event.status == "completed":
        flash("This event is completed, so staff can no longer be added.", "warning")
        return redirect(url_for("events.view_event", event_id=event.id))

    form = staff_form_for(fresh=False)
    if form.validate_on_submit():
        person = db.session.get(User, form.user_id.data)
        person.status = "in event"
        person.current_event_id = event.id
        person.save()
        flash(f"{person.full_name} was added to this event.", "success")
        log_activity("assigned", "event", f'added {person.full_name} to "{event.name}"')
        return redirect(url_for("events.view_event", event_id=event.id))

    return render_detail(event, staff_form=form, open_staff=True)


@events_bp.route("/<int:event_id>/staff/<int:user_id>/remove", methods=["POST"])
@admin_required
def remove_staff(event_id, user_id):
    person = db.get_or_404(User, user_id)
    if person.current_event_id != event_id:  # not in this event
        abort(404)
    event_name = person.current_event.name if person.current_event else "an event"
    person.status = "available"
    person.current_event_id = None
    person.save()
    flash(f"{person.full_name} was removed from this event.", "success")
    log_activity("removed", "event", f'removed {person.full_name} from "{event_name}"')
    return redirect(url_for("events.view_event", event_id=event_id))
