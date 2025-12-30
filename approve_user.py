from app import app
from extensions import db
from models.user import User

def approve_only():
    with app.app_context():
        email = input("Enter the email of the user to approve: ")
        user = User.query.filter_by(email=email).first()
        if user:
            user.is_approved = True
            user.status = "Active"
            db.session.commit()
            print(f"User {email} has been approved (Role remains: {user.role}).")
        else:
            print(f"User {email} not found.")

if __name__ == "__main__":
    approve_only()