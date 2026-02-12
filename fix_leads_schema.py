from app import app
from extensions import db
from sqlalchemy import text

def add_deleted_at_column():
    with app.app_context():
        print("--- 🔧 Adding 'deleted_at' column to leads table ---")
        try:
            with db.engine.connect() as connection:
                # Attempt to add the column
                connection.execute(text("ALTER TABLE leads ADD COLUMN deleted_at DATETIME"))
                connection.commit()
            print("✅ Column 'deleted_at' added successfully.")
        except Exception as e:
            print(f"ℹ️ Note: {e}")

if __name__ == "__main__":
    add_deleted_at_column()