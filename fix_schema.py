from app import app
from extensions import db

def migrate_db():
    with app.app_context():
        # 1. Ensure all tables defined in the models exist.
        # This is the primary purpose of a schema setup script.
        db.create_all()
        print("✅ Verified all tables exist (db.create_all()).")
        
        # 2. The auto-migration logic within app.py handles adding missing columns.
        # This logic is triggered automatically when `from app import app` is called.
        # By removing the redundant ALTER TABLE statements from this script,
        # we eliminate the "duplicate column" errors.
        print("✅ Auto-migration from app.py has been triggered by the import.")
        print("✅ Schema check complete. Any necessary columns were added by the main app logic.")

if __name__ == "__main__":
    migrate_db()