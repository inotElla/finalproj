"""Keeps each event's status (upcoming / ongoing / completed) up to date by itself.

Rules, using Philippine time:
  * An event whose date has arrived is "ongoing" (it was "upcoming" before).
  * Once its end time has passed (no end time = the end of that day), it becomes
    "completed" as soon as every equipment line has been returned. An event with
    no equipment at all completes right away.
  * If equipment is still out after the end time, it stays "ongoing" so it keeps
    showing in the dashboard's Pick-up alerts. Returning the last item completes it.
  * "completed" is never changed back.
"""
import time as clock
from datetime import datetime, time, timedelta, timezone

from app import db
from app.models import Event

PH_TZ = timezone(timedelta(hours=8))
CHECK_EVERY_SECONDS = 60  # the work runs at most once a minute, not on every click

_last_check = 0.0


def wanted_status(event, now):
    """What the status should be right now. `now` is a naive Philippine datetime."""
    if event.status == "completed" or event.event_date is None:
        return event.status
    if event.event_date > now:
        return event.status  # not started yet: leave it (normally "upcoming")
    ended_at = datetime.combine(event.event_date.date(), event.end_time or time(23, 59, 59))
    if now < ended_at:
        return "ongoing"
    everything_back = all(line.is_returned for line in event.equipment_assignments)
    return "completed" if everything_back else "ongoing"


def refresh_event_statuses(force=False):
    """Fix any status that is out of date. Safe to call often."""
    global _last_check
    if not force and clock.monotonic() - _last_check < CHECK_EVERY_SECONDS:
        return
    _last_check = clock.monotonic()

    now = datetime.now(PH_TZ).replace(tzinfo=None)
    candidates = Event.query.filter(
        Event.status != "completed", Event.event_date.isnot(None), Event.event_date <= now
    ).all()
    changed = False
    for event in candidates:
        new_status = wanted_status(event, now)
        if new_status != event.status:
            event.status = new_status
            changed = True
    if changed:
        db.session.commit()
