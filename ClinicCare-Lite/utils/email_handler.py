import os
import smtplib
from email.mime.text import MIMEText


def send_email(recipient_email, subject, body):
    sender  = os.environ.get("CLINICCARE_EMAIL_ADDRESS")
    passwd  = os.environ.get("CLINICCARE_EMAIL_PASSWORD")

    if not sender or not passwd:
        raise RuntimeError(
            "Set CLINICCARE_EMAIL_ADDRESS and CLINICCARE_EMAIL_PASSWORD to send real emails."
        )

    msg            = MIMEText(body)
    msg["Subject"] = subject
    msg["From"]    = sender
    msg["To"]      = recipient_email

    with smtplib.SMTP("smtp.gmail.com", 587) as srv:
        srv.starttls()
        srv.login(sender, passwd)
        srv.send_message(msg)
