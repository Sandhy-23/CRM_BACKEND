from app import app
from extensions import db
from sqlalchemy import text

def fix_campaign_id():
    with app.app_context():
        print("--- 🔧 Fixing 'campaigns' table ID column ---")
        try:
            with db.engine.connect() as connection:
                # 1. Disable FK checks to prevent errors (MySQL)
                connection.execute(text("SET FOREIGN_KEY_CHECKS = 0"))

                # 2. Modify column to VARCHAR(36) to fit UUIDs
                connection.execute(text("ALTER TABLE campaigns MODIFY COLUMN id VARCHAR(36) NOT NULL"))

                # 3. Re-enable FK checks
                connection.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
                connection.commit()
                print("✅ Successfully modified 'id' column to VARCHAR(36).")
        except Exception as e:
            print(f"❌ Error modifying column: {e}")
            print("Note: If using SQLite, ALTER COLUMN type is not supported directly.")

if __name__ == "__main__":
    fix_campaign_id()