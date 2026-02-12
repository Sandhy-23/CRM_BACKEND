from app import app
from extensions import db
from sqlalchemy import text

def add_column():
    with app.app_context():
        print("--- 🔧 Adding is_deleted column to deals table ---")
        try:
            with db.engine.connect() as connection:
                # Add is_deleted column
                connection.execute(text("ALTER TABLE deals ADD COLUMN is_deleted BOOLEAN DEFAULT 0"))
                # Add deleted_at column
                connection.execute(text("ALTER TABLE deals ADD COLUMN deleted_at DATETIME"))
                print("✅ Successfully added 'is_deleted' and 'deleted_at' columns to 'deals' table.")
        except Exception as e:
            print(f"❌ Error adding columns: {e}")
            print("Note: If the columns already exist, this error is expected.")

if __name__ == "__main__":
    add_column()