from app import app
from extensions import db
from models.user import User

def promote_user():
    with app.app_context():
        email = input("Enter the email of the user to promote: ")
        user = User.query.filter_by(email=email).first()
        if user:
            user.role = "Admin"
            user.is_approved = True
            user.status = "Active"
            db.session.commit()
            print(f"User {email} has been promoted to Admin and approved.")
        else:
            print(f"User {email} not found in the database.")

if __name__ == "__main__":
    promote_user()