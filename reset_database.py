from app import app
from extensions import db

def reset_database():
    """
    Drops all tables and recreates them based on the current models.
    USE WITH CAUTION IN DEVELOPMENT ONLY. This will delete all data.
    """
    with app.app_context():
        print("--- ⚠️  WARNING: This will delete ALL data in the database. ---")
        confirm = input("This is a destructive operation. Type 'reset' to continue: ")
        if confirm.lower() != 'reset':
            print("Aborted.")
            return

        print("🔥 Dropping all tables...")
        try:
            db.drop_all()
            print("✅ All tables dropped.")
        except Exception as e:
            print(f"❌ Error dropping tables: {e}")
            return

        print("🚀 Recreating all tables from models...")
        db.create_all()
        print("✅ All tables recreated successfully. You can now restart your Flask server.")

if __name__ == "__main__":
    reset_database()