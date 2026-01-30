from app import app
from extensions import db
from sqlalchemy import text

def fix_automation_tables():
    with app.app_context():
        print("🔧 Fixing Automation Tables...")
        
        with db.engine.connect() as connection:
            # Drop tables in correct order (children first to avoid FK issues)
            tables = ['automation_logs', 'automation_actions', 'automation_conditions', 'automation_rules']
            
            for table in tables:
                try:
                    connection.execute(text(f"DROP TABLE IF EXISTS {table}"))
                    print(f"   ✔ Dropped table: {table}")
                except Exception as e:
                    print(f"   ⚠️ Could not drop {table}: {e}")
            
            connection.commit()

        # Recreate tables with the correct schema from models/automation.py
        print("🔄 Recreating tables...")
        db.create_all()
        print("✅ Automation tables reset successfully. You can now create rules.")

if __name__ == "__main__":
    fix_automation_tables()