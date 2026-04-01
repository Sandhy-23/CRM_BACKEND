from app import app
from extensions import db
from sqlalchemy import text, inspect

def fix_all_schemas():
    """
    Inspects and adds missing columns to the 'notes' and 'contacts' tables
    to align the database schema with the application models.
    """
    with app.app_context():
        inspector = inspect(db.engine)
        
        # --- 1. FIX NOTES TABLE ---
        print("\n--- 🔧 Fixing 'notes' table schema ---")
        try:
            note_columns = [col['name'] for col in inspector.get_columns('notes')]
            
            with db.engine.connect() as connection:
                if 'title' not in note_columns:
                    print("   -> Adding 'title' column...")
                    connection.execute(text("ALTER TABLE notes ADD COLUMN title VARCHAR(255)"))
                else:
                    print("   -> 'title' column already exists.")
                
                # Add 'content' and migrate from old 'note' column if it exists
                if 'content' not in note_columns:
                     print("   -> Adding 'content' column...")
                     connection.execute(text("ALTER TABLE notes ADD COLUMN content TEXT"))
                     if 'note' in note_columns:
                         print("   -> Migrating data from 'note' to 'content'...")
                         connection.execute(text("UPDATE notes SET content = note WHERE content IS NULL"))
                else:
                    print("   -> 'content' column already exists.")

                connection.commit()
                print("✅ 'notes' table schema check complete.")

        except Exception as e:
            print(f"❌ An error occurred while fixing 'notes' table: {e}")

        # --- 2. FIX CONTACTS TABLE ---
        print("\n--- 🔧 Fixing 'contacts' table schema ---")
        try:
            contact_columns = [col['name'] for col in inspector.get_columns('contacts')]
            
            columns_to_add = [
                ("company", "VARCHAR(120)"), ("owner", "VARCHAR(50)"),
                ("last_contact", "VARCHAR(50)"), ("status", "VARCHAR(20)"),
                ("plan_type", "VARCHAR(50)"), ("is_deleted", "BOOLEAN"),
                ("deleted_at", "DATETIME")
            ]

            with db.engine.connect() as connection:
                for col_name, col_type in columns_to_add:
                    if col_name not in contact_columns:
                        print(f"   -> Adding '{col_name}' column...")
                        connection.execute(text(f"ALTER TABLE contacts ADD COLUMN {col_name} {col_type}"))
                
                connection.commit()
                print("✅ 'contacts' table schema check complete.")

        except Exception as e:
            print(f"❌ An error occurred while fixing 'contacts' table: {e}")

if __name__ == "__main__":
    fix_all_schemas()