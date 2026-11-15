from functools import wraps

from flask import flash, redirect, url_for
from flask_login import current_user, login_required


def admin_required(view):
    """Allow only logged-in admins. Everyone else is sent back with a message.

    Hiding a button in the template is not enough: someone can still send the
    request by hand. This check runs on the server, so it cannot be skipped.
    """

    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if current_user.role != "admin":
            flash("Only an admin can do that.", "warning")
            return redirect(url_for("main.dashboard"))
        return view(*args, **kwargs)

    return wrapped
