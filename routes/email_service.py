import smtplib
from email.mime.text import MIMEText

EMAIL = "your_email@gmail.com"
PASSWORD = "your_app_password"

def send_email(to_emails, subject, body):
    if isinstance(to_emails, str):
        to_emails = [to_emails]

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL
    msg["To"] = ", ".join(to_emails)

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL, PASSWORD)
        server.sendmail(EMAIL, to_emails, msg.as_string())
        server.quit()
        print("Email sent:", to_emails)
    except Exception as e:
        print("Email error:", e)