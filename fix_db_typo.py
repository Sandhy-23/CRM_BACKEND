from app import app
from extensions import db
from sqlalchemy import text

def fix_email_typo():
    with app.app_context():
        print("--- 🔧 Fixing Database Email Typo ---")
        try:
            # Step 2: Fix your database
            sql = text("UPDATE users SET email = 'hi@bye.com' WHERE email = 'hi@bye.com16'")
            result = db.session.execute(sql)
            db.session.commit()
            
            if result.rowcount > 0:
                print(f"✅ Success! Updated {result.rowcount} record(s).")
            else:
                print("ℹ️ No records found with email 'hi@bye.com16'.")
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    fix_email_typo()