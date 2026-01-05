from app import app
from extensions import db
from models.user import User

def reset_users():
    with app.app_context():
        # Delete all users to reset the "First User" check
        num_deleted = db.session.query(User).delete()
        db.session.commit()
        print(f"Deleted {num_deleted} users. You can now use /auth/signup to register the Super Admin.")

if __name__ == "__main__":
    reset_users()