from app import app
from extensions import db
from sqlalchemy import text

def add_db_name_column():
    with app.app_context():
        print("--- 🔧 Adding db_name column to organizations table ---")
        try:
            with db.engine.connect() as connection:
                # Add db_name column if it doesn't exist
                connection.execute(text("ALTER TABLE organizations ADD COLUMN db_name VARCHAR(255)"))
                connection.commit()
                print("✅ Successfully added 'db_name' column to 'organizations' table.")
        except Exception as e:
            if "Duplicate column name" in str(e):
                print("ℹ️ Column 'db_name' already exists.")
            else:
                print(f"❌ Error adding column: {e}")

        # Verification
        result = db.session.execute(text("SELECT id, name, db_name FROM organizations")).fetchall()
        print(f"Current mappings: {result}")

if __name__ == "__main__":
    add_db_name_column()