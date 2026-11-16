# C.A.T.E.R.

**Catering Asset Tracking and Equipment Retrieval** — a web app that helps a catering
business know what equipment it owns, which event it is out on, who is working that
event, and whether everything came back.

Built with **Flask**, **Bootstrap 5**, JavaScript and **MySQL** (final project for
IPT1 / OOP / Web Systems and Technologies, Laguna University).

## Features

| Area | What it does |
| --- | --- |
| Public home, register, login | Landing page, account creation, secure login, logout |
| Password reset (SMTP) | Emails a one-hour reset link; also emails confirmations for email/password changes |
| Dashboard | Equipment count, items out, active events, recent activity, staff overview (admin) |
| Equipment | Add, search, edit, delete. Items are tracked **by quantity** (200 plates) or **one by one** (Chafing Dish #1, #2 ...) |
| Events | Create events, assign staff and equipment, check available stock before assigning |
| Checklists | Per event: mark items packed, record what came back, flag missing items, complete the event |
| Staff | Everyone can see who is available or in an event, and what equipment that event has |
| Profile | Change name, email (with an emailed confirmation link) and password |
| Activity log | Admin-only history of who did what and when |

### Who can do what

| | Staff | Admin |
| --- | --- | --- |
| View equipment, events, staff, checklists | yes | yes |
| Add / edit equipment and units | yes | yes |
| Delete equipment and units | no | yes |
| Pack items and record returns | yes | yes |
| Create / edit / delete events, assign staff and equipment | no | yes |
| Complete an event, change a staff member's status | no | yes |
| Read the activity log | no | yes |

The **first account registered becomes the admin**. Everyone after that is staff.

## Run it on your computer

You need Python 3.10+ and MySQL (for example XAMPP).

1. **Create the database.** Start MySQL, open phpMyAdmin and create an empty database,
   for example `cater_db`.
2. **Get the code and install the packages**

   ```bash
   git clone <your repository link>
   cd <the project folder>
   python -m venv venv
   venv\Scripts\activate        # Windows.  On Mac/Linux: source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Create a file named `.env`** in the project folder (it is ignored by Git, never commit it):

   ```
   SECRET_KEY=put-a-long-random-text-here
   DATABASE_URL=mysql+pymysql://root:@localhost/cater_db

   # Email (Gmail needs an App Password, not your normal password)
   MAIL_USERNAME=youraddress@gmail.com
   MAIL_PASSWORD=your-app-password
   ```

   Without `MAIL_USERNAME` and `MAIL_PASSWORD`, emails are printed in the terminal while
   `debug=True`, so you can still test password reset.

4. **Start the app**

   ```bash
   python run.py
   ```

   Open http://127.0.0.1:5000. The tables are **created automatically** the first time
   the app starts; there is nothing to import. Register the first account (it becomes the admin).

### Settings you can add to `.env`

| Setting | Meaning |
| --- | --- |
| `SESSION_COOKIE_SECURE=true` | Send the login cookie only over https. Turn on for the online site. |
| `TRUST_PROXY=true` | Needed on Render, so the real visitor address and https are used. |
| `APP_BASE_URL=https://your-site.onrender.com` | The address used in links inside emails. |
| `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USE_TLS` | Defaults are Gmail (`smtp.gmail.com`, 587, TLS). |

## Deploying (Render + TiDB Cloud)

- Use the TiDB connection string as `DATABASE_URL` (`mysql+pymysql://...`).
- Set `SECRET_KEY`, `SESSION_COOKIE_SECURE=true`, `TRUST_PROXY=true` and `APP_BASE_URL`
  in Render's environment settings.
- Start command: `gunicorn run:app`
- Render's free plan blocks the normal SMTP ports, so a different email service (for
  example one that listens on port 2525) is needed for emails to be sent online.

## Security

- Passwords are hashed with Werkzeug (`generate_password_hash`); plain passwords are never stored.
- All database access goes through SQLAlchemy with bound parameters (no SQL injection).
- Jinja escapes everything it prints (XSS), and no user text is placed inside JavaScript.
- Every form is protected by a CSRF token (Flask-WTF `CSRFProtect`).
- Sessions use HttpOnly, SameSite cookies, end on logout, and a login without "remember me"
  expires after 8 hours. Pages of a signed-in user are sent with `Cache-Control: no-store`.
- Five wrong logins in ten minutes pause that address + email; password-reset requests are limited too.
- Admin-only actions are checked **on the server** (`@admin_required`), not just hidden in the page.
- Reset and email-change links are signed, expire after one hour and can be used once.
- Security headers: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`.

## Validation and errors

- **In the browser:** HTML5 rules (`required`, length, min/max, email) are checked by
  `app/static/js/app.js`, which shows the message under the box and prevents double submits.
- **On the server:** every form is re-checked with Flask-WTF validators, plus rules that
  need the database (duplicate names, stock available, not more returned than went out).
- **When something fails:** 404, 403, 500, a dropped database connection and expired forms
  show a friendly page or message (`app/errors.py`), never a stack trace.

## Project structure

```
run.py                  starts the app
config.py               settings read from .env
app/
  __init__.py           creates the app (create_app), registers the blueprints
  models.py             OOP classes: BaseModel -> User, Event, EventEquipment, Equipment, EquipmentUnit, ActivityLog
  forms.py              Flask-WTF forms and their validators
  activity.py           log_activity() - writes the activity log
  throttle.py           AttemptLimiter class - login / reset throttling
  errors.py             friendly error pages
  decorators.py         admin_required
  emailer.py            sending emails
  routes/               one blueprint per area (auth, main, profile, equipment, events, checklists, staff, activity)
  templates/            Jinja pages, one folder per area
  static/               CSS, JavaScript, logo
```

### OOP in this project

- `BaseModel` holds what every table shares (`id`, `created_at`, `save()`, `delete()`);
  every model **inherits** it and some **override** `delete()` to clean up related data first.
- Business rules live on the classes (**encapsulation**): `Equipment.free_quantity`,
  `Equipment.add_units()`, `Event.release()`, `EventEquipment.missing`, `User.initials`.
- `AttemptLimiter` is a small class that hides how failed attempts are counted.

## Client

_Add here: who the client is, the date and notes of the requirements interview, and their
feedback or sign-off._
