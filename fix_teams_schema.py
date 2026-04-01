from app import app
from extensions import db
from sqlalchemy import text

def add_organization_id_column():
    with app.app_context():
        print("--- 🔧 Adding 'organization_id' column to teams table ---")
        try:
            with db.engine.connect() as connection:
                # Check if column exists first (some DBs throw error on duplicate column add)
                # For MySQL/SQLite generic approach, just try adding it
                try:
                    connection.execute(text("ALTER TABLE teams ADD COLUMN organization_id INTEGER"))
                    print("✅ Column 'organization_id' added successfully.")
                except Exception as e:
                    if "duplicate column" in str(e).lower() or "exists" in str(e).lower():
                        print("ℹ️ Column 'organization_id' already exists.")
                    else:
                        print(f"❌ Error adding column: {e}")
        except Exception as e:
            print(f"❌ Connection error: {e}")

if __name__ == "__main__":
    add_organization_id_column()