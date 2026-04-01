from app import app
from extensions import db
from sqlalchemy import text, inspect

def fix_tasks_schema():
    with app.app_context():
        print("--- 🔧 Fixing tasks table schema ---")
        inspector = inspect(db.engine)
        
        try:
            columns = [col['name'] for col in inspector.get_columns('tasks')]
            
            with db.engine.connect() as connection:
                # 1. Add 'assigned_to' column if it doesn't exist
                if 'assigned_to' not in columns:
                    print("Attempting to add 'assigned_to' column...")
                    connection.execute(text("ALTER TABLE tasks ADD COLUMN assigned_to INTEGER"))
                    print("✅ Successfully added 'assigned_to' column.")
                    
                    # 2. Add Foreign Key constraint (Best Practice)
                    try:
                        print("Attempting to add foreign key constraint...")
                        connection.execute(text("ALTER TABLE tasks ADD CONSTRAINT fk_tasks_assigned_to FOREIGN KEY (assigned_to) REFERENCES users(id)"))
                        print("✅ Successfully added foreign key constraint.")
                    except Exception as fk_error:
                        print(f"⚠️ Could not add foreign key constraint (this is okay for now): {fk_error}")
                    
                    connection.commit()
                else:
                    print("✅ Column 'assigned_to' already exists.")

                # 3. Add 'description' column if it doesn't exist
                if 'description' not in columns:
                    print("Attempting to add 'description' column...")
                    connection.execute(text("ALTER TABLE tasks ADD COLUMN description TEXT"))
                    print("✅ Successfully added 'description' column.")
                else:
                    print("✅ Column 'description' already exists.")

                # 4. Add 'priority' column if it doesn't exist
                if 'priority' not in columns:
                    print("Attempting to add 'priority' column...")
                    connection.execute(text("ALTER TABLE tasks ADD COLUMN priority VARCHAR(20) DEFAULT 'medium'"))
                    print("✅ Successfully added 'priority' column.")
                else:
                    print("✅ Column 'priority' already exists.")
                
                # 5. Restore 'status' column
                if 'status' not in columns:
                    print("Attempting to add 'status' column...")
                    connection.execute(text("ALTER TABLE tasks ADD COLUMN status VARCHAR(20) DEFAULT 'pending'"))
                    print("✅ Successfully added 'status' column.")

                # 6. Fix inconsistent data
                print("Attempting to normalize task data...")
                connection.execute(text("UPDATE tasks SET status = 'pending' WHERE status IS NULL"))
                connection.commit()
                print("✅ Data normalization complete.")
            
            # --- 🔧 FIX NOTES TABLE ---
            print("\n--- 🔧 Fixing notes table schema ---")
            note_columns = [col['name'] for col in inspector.get_columns('notes')]
            
            with db.engine.connect() as connection:
                # 1. Add 'title' column if it doesn't exist
                if 'title' not in note_columns:
                    print("Attempting to add 'title' column to notes...")
                    connection.execute(text("ALTER TABLE notes ADD COLUMN title VARCHAR(255)"))
                    print("✅ Successfully added 'title' column.")
                else:
                    print("✅ Column 'title' already exists in notes.")

                # 2. Add 'content' column if it doesn't exist (Handling migration from old 'note' column)
                if 'content' not in note_columns:
                    print("Attempting to add 'content' column to notes...")
                    connection.execute(text("ALTER TABLE notes ADD COLUMN content TEXT"))
                    print("✅ Successfully added 'content' column.")
                else:
                    print("✅ Column 'content' already exists in notes.")
                
                # 3. Migrate existing data (old 'note' column -> new 'content' column)
                if 'note' in note_columns:
                    print("🔄 Migrating old data...")
                    try:
                        connection.execute(text("UPDATE notes SET content = note WHERE content IS NULL"))
                        connection.execute(text("UPDATE notes SET title = 'Untitled Note' WHERE title IS NULL"))
                        print("✅ Data migration successful.")
                    except Exception as e:
                        print(f"⚠️ Data migration skipped: {e}")

                connection.commit()

        except Exception as e:
            print(f"❌ An error occurred: {e}")

if __name__ == "__main__":
    fix_tasks_schema()