from app import app
from extensions import db
from models.user import User, LoginHistory
from models.organization import Organization
from models.activity_log import ActivityLog

# Robust imports to handle missing models during development
try: from models.task import Task
except ImportError: Task = None
try: from models.contact import Contact
except ImportError: Contact = None
try: from models.attendance import Attendance
except ImportError: Attendance = None
try: from models.crm import Lead, Deal, Activity, Ticket, Campaign
except ImportError: Lead = Deal = Activity = Ticket = Campaign = None

def reset_users():
    with app.app_context():
        print("🧹 Clearing database to allow fresh Super Admin signup...")
        
        try:
            def safe_delete(model):
                if model:
                    try:
                        db.session.query(model).delete()
                    except Exception:
                        pass

            # Delete child tables first to avoid FK constraints
            safe_delete(LoginHistory)
            safe_delete(ActivityLog)
            safe_delete(Attendance)
            safe_delete(Task)
            safe_delete(Contact)
            
            # CRM tables
            safe_delete(Lead)
            safe_delete(Deal)
            safe_delete(Activity)
            safe_delete(Ticket)
            safe_delete(Campaign)
            
            # Delete Users
            num_users = db.session.query(User).delete()
            
            # Delete Organizations (optional, but keeps it clean)
            num_orgs = db.session.query(Organization).delete()
            
            db.session.commit()
            print(f"✅ Deleted {num_users} users and {num_orgs} organizations.")
            print("🚀 System reset. You can now use /auth/signup to register the first user (Super Admin).")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error resetting database: {e}")

if __name__ == "__main__":
    reset_users()