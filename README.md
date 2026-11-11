# c.a.t.e.r

# Catering Asset Tracking and Equipment Retrieval

## Password reset email

The login page includes a password-reset link. To send reset emails, configure
these environment variables (for example, in the untracked `.env` file):

```text
SECRET_KEY=<a long, random secret>
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=<your SMTP account>
MAIL_PASSWORD=<your SMTP app password>
MAIL_DEFAULT_SENDER=<the sender address approved by your SMTP provider>
```

For Gmail, use an App Password rather than your normal account password.
Reset links expire after one hour. In production, serve the app over HTTPS and
make sure its public hostname is used when generating links.
=======