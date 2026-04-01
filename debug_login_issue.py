from app import app
from models.user import User
from sqlalchemy import func

def debug_login():
    with app.app_context():
        print("\n🔍 DEBUGGING LOGIN ISSUE...")
        
        target_email = "sandhyarani@gmail.com"
        print(f"👉 Looking for: '{target_email}'")

        # 1. Direct Search
        user = User.query.filter_by(email=target_email).first()
        if user:
            print(f"✅ User FOUND in DB!")
            print(f"   ID: {user.id}")
            print(f"   Email: {user.email}")
            print(f"   Password Hash: {user.password[:20]}...")
            return

        # 2. Case Insensitive Search
        user_ci = User.query.filter(func.lower(User.email) == target_email.lower()).first()
        if user_ci:
            print(f"⚠️ User found but casing mismatches!")
            print(f"   DB Email: '{user_ci.email}'")
            print(f"   Input Email: '{target_email}'")
            print("   👉 Fix: Ensure you type the email exactly as registered.")
            return

        # 3. List All Users
        print(f"❌ User '{target_email}' NOT found in DB.")
        print("   Current Users in Database:")
        users = User.query.all()
        if not users:
            print("   (No users found in database)")
        for u in users:
            print(f"   - {repr(u.email)}")

if __name__ == "__main__":
    debug_login()