import smtplib
import os
from dotenv import load_dotenv, find_dotenv

# Load environment variables from .env file
env_path = find_dotenv()
print(f"Loading .env from: {env_path}")
load_dotenv(env_path)

def test_smtp_connection():
    smtp_server = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.environ.get('MAIL_PORT', 587))
    smtp_user = os.environ.get('MAIL_USERNAME')
    smtp_password = os.environ.get('MAIL_PASSWORD')

    print("--- SMTP Configuration Check ---")
    print(f"MAIL_SERVER: {smtp_server}")
    print(f"MAIL_PORT: {smtp_port}")
    print(f"MAIL_USERNAME: {smtp_user}")
    
    if smtp_user == "your_email@gmail.com":
        print("❌ ERROR: You are using the placeholder email 'your_email@gmail.com'.")
        print("   -> Please open .env and replace it with your actual Gmail address.")
        return

    if not smtp_password:
        print("❌ MAIL_PASSWORD is missing in .env file!")
        return

    # Mask password for security but show length
    print(f"MAIL_PASSWORD: {'*' * len(smtp_password)} (Length: {len(smtp_password)})")

    if len(smtp_password) != 16:
        print(f"⚠️ WARNING: App Passwords are exactly 16 characters. Yours is {len(smtp_password)}.")
        print("   -> Check for spaces or hidden characters in your .env file.")

    if " " in smtp_password:
        print("❌ ERROR: Password contains spaces. Please remove spaces in .env file.")
        # We continue anyway to show the server response
    
    print("\nAttempting to connect to Gmail SMTP...")

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(smtp_user, smtp_password)
        print("✅ SUCCESS! Username and Password are correct.")
        server.quit()
    except Exception as e:
        print(f"❌ FAILED: {e}")
        print("\nTroubleshooting Tips:")
        print("1. Ensure you are using a Google App Password (16 chars), NOT your Gmail login password.")
        print(f"2. Make sure this App Password was generated specifically for the account: {smtp_user}")
        print("3. Ensure 2-Step Verification is ENABLED on your Google Account.")
        print("4. If you changed .env recently, this script loads the latest version.")

if __name__ == "__main__":
    test_smtp_connection()