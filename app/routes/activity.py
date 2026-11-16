from datetime import datetime, timedelta, timezone

from flask import Blueprint, render_template, request

from flask_login import login_required
from app.models import ActivityLog
from app.routes.main import PH_TZ

activity_bp = Blueprint("activity", __name__, url_prefix="/activity")

PER_PAGE = 20


def chosen_range(month_text, date_text):
    """Turn the picked month or day into (start, end, label), ready for the database.

    A specific day wins over a month. Anything that is not a real date is ignored,
    so typing nonsense in the address bar just shows the whole log."""
    try:
        if date_text:
            first = datetime.strptime(date_text, "%Y-%m-%d")
            start = first.replace(tzinfo=PH_TZ)
            end = start + timedelta(days=1)
            label = first.strftime("%B %d, %Y")
        elif month_text:
            first = datetime.strptime(month_text, "%Y-%m")
            start = first.replace(tzinfo=PH_TZ)
            # Adding 4 days to the 28th always lands in next month; day=1 is its first day.
            end = (first.replace(day=28) + timedelta(days=4)).replace(day=1).replace(tzinfo=PH_TZ)
            label = first.strftime("%B %Y")
        else:
            return None
    except ValueError:
        return None

    # Times are stored in UTC, but a "day" means a Philippine day (UTC+8), so the
    # boundaries are converted to UTC before comparing.
    def to_db(moment):
        return moment.astimezone(timezone.utc).replace(tzinfo=None)

    return to_db(start), to_db(end), label


@activity_bp.route("/")
@login_required  # any signed-in user may read the log
def list_activity():
    # request.args holds the ?month=...&date=...&page=... part of the address.
    month_text = request.args.get("month", "").strip()
    date_text = request.args.get("date", "").strip()
    page = request.args.get("page", 1, type=int)  # type=int: "abc" falls back to 1

    query = ActivityLog.query
    picked = chosen_range(month_text, date_text)
    if picked:
        start, end, label = picked
        query = query.filter(ActivityLog.created_at >= start, ActivityLog.created_at < end)
    else:
        label = None

    # Newest first. id is the tie-breaker for lines written in the same second.
    pagination = query.order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc()).paginate(
        page=page, per_page=PER_PAGE, error_out=False
    )
    return render_template(
        "activity/activity_list.html",
        pagination=pagination,
        label=label,
        # Only a valid pick is shown again in the boxes. A day takes over from a month.
        date_value=date_text if picked and date_text else "",
        month_value=month_text if picked and not date_text else "",
        today=datetime.now(PH_TZ).strftime("%Y-%m-%d"),
    )
