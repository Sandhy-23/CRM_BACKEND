from app import app
from extensions import db
from models.user import User, LoginHistory
from models.organization import Organization
from models.activity_log import ActivityLog
from models.task import Task
from models.contact import Contact
from models.attendance import Attendance
from models.crm import Lead, Deal, Activity, Ticket, Campaign

def reset_users():
    with app.app_context():
        print("Clearing database...")
        
        try:
            # Delete child tables first to avoid FK constraints
            db.session.query(LoginHistory).delete()
            db.session.query(ActivityLog).delete()
            db.session.query(Attendance).delete()
            db.session.query(Task).delete()
            db.session.query(Contact).delete()
            
            # CRM tables
            db.session.query(Lead).delete()
            db.session.query(Deal).delete()
            db.session.query(Activity).delete()
            db.session.query(Ticket).delete()
            db.session.query(Campaign).delete()
            
            # Delete Users
            num_users = db.session.query(User).delete()
            
            # Delete Organizations (optional, but keeps it clean)
            num_orgs = db.session.query(Organization).delete()
            
            db.session.commit()
            print(f"Deleted {num_users} users and {num_orgs} organizations.")
            print("System reset. You can now use /auth/signup to register the first user (Super Admin).")
        except Exception as e:
            db.session.rollback()
            print(f"Error resetting database: {e}")

if __name__ == "__main__":
    reset_users()