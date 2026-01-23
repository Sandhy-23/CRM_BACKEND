from app import app
from extensions import db
from models.user import User
from werkzeug.security import generate_password_hash

def interactive_reset():
    with app.app_context():
        print("\n--- 🔍 EXISTING USERS ---")
        users = User.query.all()
        if not users:
            print("❌ No users found in the database.")
            return

        for u in users:
            print(f"ID: {u.id} | Email: {u.email} | Role: {u.role} | Verified: {u.is_verified}")
        
        print("-------------------------")
        target_input = input("\nEnter the ID (number) of the user to reset: ").strip()
        
        if not target_input.isdigit():
             print("❌ Please enter a valid numeric User ID from the list above.")
             return

        user = User.query.get(int(target_input))
            
        if not user:
            print(f"❌ User ID {target_input} not found.")
            return

        new_pass = "password123"
        print(f"   -> Resetting password for: {user.email}")
        
        user.password = generate_password_hash(new_pass)
        user.is_verified = True # Force verify just in case
        
        db.session.commit()
        print(f"✅ Success! Password set to: {new_pass}")
        print(f"✅ Account marked as Verified.")

if __name__ == "__main__":
    interactive_reset()