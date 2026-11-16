from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required
from sqlalchemy.exc import IntegrityError

from app import db
from app.activity import log_activity
from app.decorators import admin_required
from app.forms import AddUnitsForm, EquipmentForm, UnitForm
from app.models import CATEGORIES, Equipment, EquipmentUnit

equipment_bp = Blueprint("equipment", __name__, url_prefix="/equipment")

PER_PAGE = 10


def clean_name(text):
    # " ".join(text.split()) collapses extra spaces: "  Gold   Spoons " -> "Gold Spoons"
    return " ".join(text.split())


def plural(count, word):
    return f"{count} {word}" + ("" if count == 1 else "s")


# ---------- Page builders ----------


def render_list(add_form=None, open_add=False):
    """The equipment list. open_add=True starts with the add form open (after an error)."""
    # request.args holds the ?q=...&category=...&page=... part of the address.
    q = request.args.get("q", "").strip()[:100]
    category = request.args.get("category", "")
    page = request.args.get("page", 1, type=int)  # type=int: "abc" falls back to 1

    query = Equipment.query
    if q:
        # ilike = case-insensitive LIKE. The value travels as a bound parameter,
        # never pasted into the SQL text, so typing quotes or SQL cannot change the query.
        query = query.filter(Equipment.name.ilike(f"%{q}%"))
    if category in CATEGORIES:  # an unknown category is simply ignored
        query = query.filter(Equipment.category == category)

    pagination = query.order_by(Equipment.name).paginate(
        page=page, per_page=PER_PAGE, error_out=False
    )
    if add_form is None:
        # formdata=None: start with an empty form, ignore anything in request.form
        add_form = EquipmentForm(formdata=None)

    return render_template(
        "equipments/equipment_list.html",
        pagination=pagination,
        q=q,
        category=category,
        categories=CATEGORIES,
        add_form=add_form,
        open_add=open_add,
    )


def render_detail(equipment, units_form=None, open_units=False):
    """The equipment page: its details and, for one-by-one items, its units."""
    units = (
        EquipmentUnit.query.filter_by(equipment_id=equipment.id)
        .order_by(EquipmentUnit.code)
        .all()
    )
    if units_form is None:
        units_form = AddUnitsForm(formdata=None)
    return render_template(
        "equipments/equipment_detail.html",
        equipment=equipment,
        units=units,
        units_form=units_form,
        open_units=open_units,
    )


# ---------- Equipment: list, add, view, edit, delete ----------


@equipment_bp.route("/")
@login_required
def list_equipment():
    return render_list()


@equipment_bp.route("/new", methods=["GET", "POST"])
@login_required
def create_equipment():
    if request.method == "GET":
        # The add form lives on the list page, behind the "+ Add equipment" button.
        return redirect(url_for("equipment.list_equipment"))

    form = EquipmentForm()
    if form.validate_on_submit():
        quantity = form.quantity_total.data
        tracking_type = form.tracking_type.data

        equipment = Equipment(
            name=clean_name(form.name.data),
            category=form.category.data,
            tracking_type=tracking_type,
            # one-by-one items count their units, so no separate number is stored
            quantity_total=quantity if tracking_type == "bulk" else 0,
        )
        equipment.save()

        if tracking_type == "individual":
            try:
                equipment.add_units(quantity)
            except IntegrityError:
                db.session.rollback()
                flash(
                    f'"{equipment.name}" was added, but its units could not be created. '
                    "Add them from the item page.",
                    "warning",
                )
                return redirect(url_for("equipment.view_equipment", equipment_id=equipment.id))
            flash(f'"{equipment.name}" was added with {plural(quantity, "unit")}.', "success")
            log_activity("created", "equipment", f'added equipment "{equipment.name}" with {plural(quantity, "unit")}')
        else:
            flash(f'"{equipment.name}" was added ({quantity} in stock).', "success")
            log_activity("created", "equipment", f'added equipment "{equipment.name}" ({quantity} in stock)')
        return redirect(url_for("equipment.view_equipment", equipment_id=equipment.id))

    # Something was wrong: show the list again with the add form open and its errors.
    return render_list(add_form=form, open_add=True)


@equipment_bp.route("/<int:equipment_id>")
@login_required
def view_equipment(equipment_id):
    # get_or_404 shows a "not found" page instead of crashing when the id does not exist
    equipment = db.get_or_404(Equipment, equipment_id)
    return render_detail(equipment)


@equipment_bp.route("/<int:equipment_id>/edit", methods=["GET", "POST"])
@login_required
def edit_equipment(equipment_id):
    equipment = db.get_or_404(Equipment, equipment_id)
    # obj=equipment pre-fills the boxes on GET; equipment=equipment lets the form's
    # own checks ignore this item when looking for a duplicate name.
    form = EquipmentForm(obj=equipment, equipment=equipment)

    if form.validate_on_submit():
        old_name = equipment.name
        was_type = equipment.tracking_type
        new_type = form.tracking_type.data
        new_name = clean_name(form.name.data)
        quantity = form.quantity_total.data
        renamed = new_name != equipment.name

        equipment.name = new_name
        equipment.category = form.category.data
        equipment.tracking_type = new_type
        if new_type == "bulk":
            equipment.quantity_total = quantity
        else:
            equipment.quantity_total = 0  # one-by-one items count their units
        equipment.save()

        if renamed:
            equipment.refresh_unit_labels()  # units are named after the equipment
        if was_type == "bulk" and new_type == "individual":
            equipment.add_units(quantity)  # the quantity becomes that many units

        flash("Equipment updated.", "success")
        if renamed:
            log_activity("updated", "equipment", f'renamed equipment "{old_name}" to "{equipment.name}"')
        else:
            log_activity("updated", "equipment", f'updated equipment "{equipment.name}"')
        return redirect(url_for("equipment.view_equipment", equipment_id=equipment.id))

    return render_template("equipments/equipment_form.html", form=form, equipment=equipment)


@equipment_bp.route("/<int:equipment_id>/delete", methods=["POST"])
@admin_required
def delete_equipment(equipment_id):
    equipment = db.get_or_404(Equipment, equipment_id)
    busy = equipment.active_assignment_count
    if busy:
        # Deleting it now would silently remove it from events that still need it.
        flash(
            f'"{equipment.name}" is on {plural(busy, "active event")}. '
            "Remove it from them first, or complete those events.",
            "warning",
        )
        return redirect(url_for("equipment.view_equipment", equipment_id=equipment.id))
    name = equipment.name
    equipment.delete()  # its units and event assignments go with it (see models.py)
    flash(f'"{name}" and its units were deleted.', "success")
    log_activity("deleted", "equipment", f'deleted equipment "{name}"')
    return redirect(url_for("equipment.list_equipment"))


# ---------- Units (items tracked one by one) ----------


@equipment_bp.route("/<int:equipment_id>/units", methods=["POST"])
@login_required
def add_units(equipment_id):
    equipment = db.get_or_404(Equipment, equipment_id)
    if equipment.tracking_type != "individual":
        flash("This equipment is tracked by quantity. Change its quantity by editing it.", "warning")
        return redirect(url_for("equipment.view_equipment", equipment_id=equipment.id))

    form = AddUnitsForm()
    if form.validate_on_submit():
        count = form.count.data
        try:
            equipment.add_units(count, condition=form.condition.data)
        except IntegrityError:
            db.session.rollback()
            flash("Those units could not be created. Please try again.", "danger")
            return render_detail(equipment, units_form=form, open_units=True)

        flash(f"Added {plural(count, 'unit')}.", "success")
        log_activity("created", "unit", f'added {plural(count, "unit")} to "{equipment.name}"')
        return redirect(url_for("equipment.view_equipment", equipment_id=equipment.id))

    return render_detail(equipment, units_form=form, open_units=True)


@equipment_bp.route("/units/<int:unit_id>/edit", methods=["GET", "POST"])
@login_required
def edit_unit(unit_id):
    unit = db.get_or_404(EquipmentUnit, unit_id)
    form = UnitForm(obj=unit)

    if form.validate_on_submit():
        unit.condition = form.condition.data
        unit.status = form.status.data
        unit.save()
        flash(f"{unit.code} was updated.", "success")
        log_activity("updated", "unit", f"updated {unit.code} (condition: {unit.condition}, status: {unit.status})")
        return redirect(url_for("equipment.view_equipment", equipment_id=unit.equipment_id))

    return render_template("equipments/unit_form.html", form=form, unit=unit)


@equipment_bp.route("/units/<int:unit_id>/delete", methods=["POST"])
@admin_required
def delete_unit(unit_id):
    unit = db.get_or_404(EquipmentUnit, unit_id)
    if unit.status == "out":
        flash(f"{unit.code} is out on an event. Return it first, then delete it.", "warning")
        return redirect(url_for("equipment.view_equipment", equipment_id=unit.equipment_id))
    equipment_id, name = unit.equipment_id, unit.code
    unit.delete()
    flash(f"{name} was deleted.", "success")
    log_activity("deleted", "unit", f"deleted {name}")
    return redirect(url_for("equipment.view_equipment", equipment_id=equipment_id))


