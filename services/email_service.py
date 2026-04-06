import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os

def send_user_email(to_email, name, password):
    # Load credentials from .env
    from_email = os.getenv("MAIL_USERNAME")
    app_password = os.getenv("MAIL_PASSWORD")
    frontend_url = os.getenv("FRONTEND_URL", "http://100.104.233.79:5173/")

    print("LOGIN URL DEBUG:", frontend_url)

    if not from_email or not app_password:
        print("❌ Email skipped: MAIL_USERNAME or MAIL_PASSWORD not set in .env")
        return

    subject = "Welcome! Your Login Details"

    body = f"""
    <html>
    <body style="font-family: Arial; background-color:#111; color:white; padding:20px;">
        <h2>Welcome {name}!</h2>
        <p>Now access all your CRM content from anywhere.</p>

        <h3>Here are your Login details:</h3>

        <div style="background:#222; padding:15px; border-radius:10px;">
            <p><b>Web Address:</b><br> {frontend_url}</p>
            <p><b>Username:</b><br> {to_email}</p>
            <p><b>Password:</b><br> {password}</p>
        </div>

        <p style="margin-top:20px;">
        Thank you for joining.
        </p>
    </body>
    </html>
    """

    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(from_email, app_password)
            server.send_message(msg)
        print("✅ Email sent successfully")
    except Exception as e:
        print(f"❌ Email sending failed: {str(e)}")