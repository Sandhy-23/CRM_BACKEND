from flask_mail import Message
from extensions import mail
from flask import current_app

def send_payment_email(to_email, payment_url):
    """
    Sends the CRM subscription payment link email.
    """
    try:
        msg = Message(
            subject="Complete Your CRM Subscription Payment",
            sender=current_app.config.get('MAIL_USERNAME'),
            recipients=[to_email]
        )

        msg.body = f"""
    Please complete your CRM subscription payment using the link below:

    {payment_url}
    """
        mail.send(msg)
    except Exception as e:
        print(f"[FAIL] Could not send payment email: {e}")

def send_email(to_email, subject, body):
    """
    Generic email sending function used by other parts of the app, like the scheduler.
    """
    if not current_app.config.get('MAIL_USERNAME'):
        print("[WARN] MAIL_USERNAME not set. Skipping email.")
        return

    try:
        msg = Message(
            subject=subject,
            sender=current_app.config.get('MAIL_USERNAME'),
            recipients=[to_email],
            body=body
        )
        mail.send(msg)
    except Exception as e:
        print(f"[FAIL] Could not send generic email: {e}")