from app import app
from models.user import User

def list_all_users():
    with app.app_context():
        users = User.query.all()
        print("\n--- Registered Users ---")
        for user in users:
            print(f"ID: {user.id} | Email: {user.email} | Role: {user.role} | Approved: {user.is_approved}")
        print("------------------------\n")

if __name__ == "__main__":
    list_all_users()