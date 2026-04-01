from app import app
from models.user import User

def list_users():
    with app.app_context():
        print("\n--- 🔍 CURRENT DATABASE USERS ---")
        users = User.query.all()
        
        if not users:
            print("❌ No users found in database.")
            return

        print(f"{'ID':<5} | {'Email (Exact)':<35} | {'Password (Hash/Plain)'}")
        print("-" * 65)
        
        for u in users:
            # repr() shows hidden characters like ' ' as quotes 'email '
            print(f"{u.id:<5} | {repr(u.email):<35} | {u.password[:15]}...")
        
        print("-" * 65)

if __name__ == "__main__":
    list_users()