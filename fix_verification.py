from app import app
from extensions import db
from models.user import User

def fix_verification():
    with app.app_context():
        print("--- 🔧 Fix User Verification ---")
        email = input("Enter email to verify: ").strip()
        user = User.query.filter_by(email=email).first()
        
        if not user:
            print(f"❌ User '{email}' not found.")
            print("👉 Available Users:")
            for u in User.query.all():
                print(f"   - {u.email} (Verified: {u.is_verified})")
            return
            
        print(f"Current Status: Verified={user.is_verified}")
        
        if not user.is_verified:
            user.is_verified = True
            db.session.commit()
            print(f"✅ Updated {email} to Verified.")
        else:
            print("✅ User is already verified.")

if __name__ == "__main__":
    fix_verification()