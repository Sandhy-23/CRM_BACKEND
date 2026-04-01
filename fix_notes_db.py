from app import app
from extensions import db
from sqlalchemy import text

def fix_notes_schema():
    """
    Standardizes the 'notes' table to use the 'content' column.
    """
    with app.app_context():
        print("--- 🔧 Standardizing Notes Table Schema ---")
        try:
            with db.engine.connect() as connection:
                # 1. Check if 'content' column exists
                try:
                    connection.execute(text("SELECT content FROM notes LIMIT 1"))
                    print("✅ Column 'content' already exists.")
                except Exception:
                    print("⚠️ Column 'content' missing. Adding it...")
                    connection.execute(text("ALTER TABLE notes ADD COLUMN content TEXT"))
                    connection.commit()
                    print("✅ Added 'content' column.")

                # 2. Migrate data from 'note' to 'content' if 'note' exists
                try:
                    connection.execute(text("UPDATE notes SET content = note WHERE content IS NULL AND note IS NOT NULL"))
                    connection.commit()
                    print("✅ Migrated data from old 'note' column to 'content'.")
                except Exception:
                    pass # 'note' column might not exist, which is fine

        except Exception as e:
            print(f"❌ Error fixing notes table: {e}")

if __name__ == "__main__":
    fix_notes_schema()