from flask import Blueprint, abort, flash, redirect, render_template, url_for
from flask_login import login_required

from app import db
from app.activity import log_activity
from app.decorators import admin_required
from app.forms import ReturnForm
from app.models import Event, EventEquipment

checklists_bp = Blueprint("checklists", __name__, url_prefix="/checklists")


# ---------- Helpers ----------


def get_open_line(event_id, line_id):
    """Find one checklist line, and make sure it really belongs to this event.

    Returns (event, line). A completed event is locked: its checklist is a record
    of what happened, so nothing on it can be changed any more."""
    event = db.get_or_404(Event, event_id)
    line = db.get_or_404(EventEquipment, line_id)
    if line.event_id != event.id:
        abort(404)  # the line belongs to some other event
    return event, line


def label(line):
    """How an item is named in the log: 'Plate x 40' or 'Chafing Dish #1'."""
    name = line.equipment.name if line.equipment else "Removed item"
    return line.unit.code if line.unit else f"{name} x {line.quantity}"


def locked_redirect(event):
    flash("This event is completed, so its checklist can no longer be changed.", "warning")
    return redirect(url_for("checklists.view_checklist", event_id=event.id))


# ---------- Pages ----------


@checklists_bp.route("/")
@login_required
def list_checklists():
    # Events still happening come first. Finished ones are kept below as a record.
    active = (
        Event.query.filter(Event.status != "completed")
        .order_by(Event.status.asc(), Event.event_date.asc())
        .all()
    )
    done = (
        Event.query.filter(Event.status == "completed")
        .order_by(Event.event_date.desc(), Event.id.desc())
        .limit(10)
        .all()
    )
    return render_template("checklists/checklist_list.html", active=active, done=done)


@checklists_bp.route("/<int:event_id>")
@login_required
def view_checklist(event_id):
    event = db.get_or_404(Event, event_id)
    return render_template(
        "checklists/checklist_detail.html",
        event=event,
        lines=sorted(event.equipment_assignments, key=lambda l: (l.equipment.name if l.equipment else "", l.id)),
        locked=event.status == "completed",
    )


# ---------- Packing (before the event) ----------


@checklists_bp.route("/<int:event_id>/items/<int:line_id>/pack", methods=["POST"])
@login_required
def toggle_packed(event_id, line_id):
    event, line = get_open_line(event_id, line_id)
    if event.status == "completed":
        return locked_redirect(event)
    if line.is_returned:
        flash("Undo the return first, then change the packing.", "warning")
        return redirect(url_for("checklists.view_checklist", event_id=event.id))

    line.packed = not line.packed  # packed <-> not packed
    line.save()
    log_activity(
        "packed", "checklist",
        f'{"packed" if line.packed else "unpacked"} {label(line)} for "{event.name}"',
    )
    return redirect(url_for("checklists.view_checklist", event_id=event.id))


@checklists_bp.route("/<int:event_id>/pack-all", methods=["POST"])
@login_required
def pack_all(event_id):
    event = db.get_or_404(Event, event_id)
    if event.status == "completed":
        return locked_redirect(event)

    changed = 0
    for line in event.equipment_assignments:
        if not line.packed and not line.is_returned:
            line.packed = True
            changed += 1
    db.session.commit()
    if changed:
        log_activity("packed", "checklist", f'marked {changed} item{"" if changed == 1 else "s"} as packed for "{event.name}"')
    flash(f"Marked {changed} item{'' if changed == 1 else 's'} as packed." if changed else "Everything is already packed.", "success" if changed else "info")
    return redirect(url_for("checklists.view_checklist", event_id=event.id))


# ---------- Returns (after the event) ----------


@checklists_bp.route("/<int:event_id>/items/<int:line_id>/return", methods=["POST"])
@login_required
def record_return(event_id, line_id):
    event, line = get_open_line(event_id, line_id)
    if event.status == "completed":
        return locked_redirect(event)
    if not line.packed:
        flash("Mark the item as packed before recording its return.", "warning")
        return redirect(url_for("checklists.view_checklist", event_id=event.id))

    form = ReturnForm()
    if not form.validate_on_submit():
        problems = [msg for errors in form.errors.values() for msg in errors]
        flash("Could not save the return: " + " ".join(problems), "danger")
        return redirect(url_for("checklists.view_checklist", event_id=event.id))

    returned = form.returned_quantity.data
    if returned > line.quantity:
        flash(f"You cannot return more than the {line.quantity} that went out.", "danger")
        return redirect(url_for("checklists.view_checklist", event_id=event.id))

    line.returned_quantity = returned
    line.issue_note = " ".join(form.issue_note.data.split()) if form.issue_note.data else None

    # A one-by-one unit has a status of its own: back on the shelf, or lost.
    if line.unit is not None:
        line.unit.status = "available" if returned >= 1 else "lost"

    db.session.commit()

    summary = f'recorded the return of {label(line)} for "{event.name}": {returned} of {line.quantity} back'
    if line.missing:
        summary += f", {line.missing} missing"
    log_activity("returned", "checklist", summary)

    if line.missing:
        flash(f"Return saved. {line.missing} not returned.", "warning")
    else:
        flash("Return saved.", "success")
    return redirect(url_for("checklists.view_checklist", event_id=event.id))


@checklists_bp.route("/<int:event_id>/items/<int:line_id>/undo-return", methods=["POST"])
@login_required
def undo_return(event_id, line_id):
    event, line = get_open_line(event_id, line_id)
    if event.status == "completed":
        return locked_redirect(event)

    line.returned_quantity = None
    line.issue_note = None
    if line.unit is not None:
        line.unit.status = "out"  # it is out with the event again
    db.session.commit()
    flash("Return undone.", "info")
    log_activity("returned", "checklist", f'undid the return of {label(line)} for "{event.name}"')
    return redirect(url_for("checklists.view_checklist", event_id=event.id))


# ---------- Finishing (admin only) ----------


@checklists_bp.route("/<int:event_id>/complete", methods=["POST"])
@admin_required
def complete_event(event_id):
    event = db.get_or_404(Event, event_id)
    if event.status == "completed":
        return locked_redirect(event)
    if event.line_count and not event.all_returned:
        flash("Record the return of every item before completing the event.", "warning")
        return redirect(url_for("checklists.view_checklist", event_id=event.id))

    event.release()  # frees the staff and any unit still marked out
    event.status = "completed"
    event.save()
    flash("Event completed. Its staff are free again.", "success")
    log_activity("completed", "event", f'completed event "{event.name}"')
    return redirect(url_for("checklists.view_checklist", event_id=event.id))
