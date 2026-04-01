from app import app
from extensions import db
from models.user import User
from models.organization import Organization
from werkzeug.security import generate_password_hash

def ensure_user():
    with app.app_context():
        # DEFINING THE CORRECT CREDENTIALS
        target_email = "sandhyarani@gmail.com"
        target_password = "sandhya23"
        
        print(f"\n--- 🔧 ENSURING USER EXISTS ---")
        print(f"Target: {target_email}")
        
        # 1. Check if user exists
        user = User.query.filter_by(email=target_email).first()
        
        if not user:
            print("❌ User not found. Creating new Super Admin...")
            
            # Ensure an organization exists
            org = Organization.query.first()
            if not org:
                org = Organization(name="Default Org", subscription_plan="Free")
                db.session.add(org)
                db.session.commit()
                print("   -> Created Default Organization")

            user = User(
                name="Sandhya Rani",
                email=target_email,
                password=generate_password_hash(target_password),
                role="Super Admin",
                organization_id=org.id,
                is_approved=True,
                status="Active",
                is_verified=True
            )
            db.session.add(user)
            db.session.commit()
            print("✅ User Created Successfully.")
        else:
            print("✅ User exists. Resetting password to ensure access...")
            user.password = generate_password_hash(target_password)
            user.is_verified = True
            user.status = "Active"
            db.session.commit()
            print("✅ Password updated.")

        print("\n👇 USE THESE EXACT CREDENTIALS IN POSTMAN 👇")
        print("---------------------------------------------")
        print(f'   "email": "{target_email}"')
        print(f'   "password": "{target_password}"')
        print("---------------------------------------------")

if __name__ == "__main__":
    ensure_user()