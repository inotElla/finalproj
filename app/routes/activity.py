from flask import Blueprint, render_template, request
from sqlalchemy import or_

from app.decorators import admin_required
from app.models import ACTIVITY_TYPES, ActivityLog

activity_bp = Blueprint("activity", __name__, url_prefix="/activity")

PER_PAGE = 20


@activity_bp.route("/")
@admin_required  # the log shows what everyone did, so only admins read it
def list_activity():
    # request.args holds the ?q=...&type=...&page=... part of the address.
    q = request.args.get("q", "").strip()[:100]
    entity_type = request.args.get("type", "")
    page = request.args.get("page", 1, type=int)  # type=int: "abc" falls back to 1

    query = ActivityLog.query
    if q:
        like = f"%{q}%"
        query = query.filter(or_(ActivityLog.summary.ilike(like), ActivityLog.user_name.ilike(like)))
    if entity_type in ACTIVITY_TYPES:  # an unknown value is simply ignored
        query = query.filter(ActivityLog.entity_type == entity_type)

    # Newest first. id is the tie-breaker for lines written in the same second.
    pagination = query.order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc()).paginate(
        page=page, per_page=PER_PAGE, error_out=False
    )
    return render_template(
        "activity/activity_list.html",
        pagination=pagination,
        q=q,
        entity_type=entity_type,
        types=ACTIVITY_TYPES,
    )
