from app import app
from extensions import db
from models.user import User, LoginHistory

def delete_user(email):
    with app.app_context():
        print(f"🔍 Searching for user: {email}...")
        user = User.query.filter_by(email=email).first()
        
        if not user:
            print(f"⚠️ User '{email}' not found in database.")
            return

        print(f"   -> Found user: {user.name} (ID: {user.id})")

        try:
            # 1. Delete Login History first (to avoid Foreign Key errors)
            deleted_logs = LoginHistory.query.filter_by(user_id=user.id).delete()
            if deleted_logs > 0:
                print(f"   -> Deleted {deleted_logs} login history records.")

            # 2. Delete the User
            db.session.delete(user)
            db.session.commit()
            print(f"✅ User '{email}' deleted successfully! You can now reuse this email.")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error deleting user: {e}")

if __name__ == "__main__":
    # Change this email if you need to delete a different user
    delete_user("test@example.com")