from flask import current_app
from flask_login import current_user

from app import db
from app.models import ActivityLog


def log_activity(action, entity_type, summary, actor=None):
    """Write one line to the activity log.

    action      -- what kind of thing happened: "created", "updated", "deleted", ...
    entity_type -- what it happened to: "equipment", "event", "checklist", ...
    summary     -- the sentence shown on the page: 'added equipment "Plate"'
    actor       -- the user who did it. Left out, it is whoever is logged in right now.

    Call this AFTER the real change has been saved. The log is only a record, so if
    writing it ever fails, the failure is noted in the server log and the user's
    action is NOT undone and NOT blocked."""
    try:
        if actor is None and current_user.is_authenticated:
            actor = current_user
        db.session.add(
            ActivityLog(
                user_id=actor.id if actor else None,
                # The name is copied into the log on purpose. If the person later
                # renames themselves or is deleted, the old entries still read correctly.
                user_name=actor.full_name if actor else "System",
                action=action,
                entity_type=entity_type,
                summary=summary[:255],  # the column holds 255 characters
            )
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Could not write the activity log")
