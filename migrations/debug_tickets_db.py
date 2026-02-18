from app import app
from extensions import db
from sqlalchemy import text
import os

def run_debug():
    print("\n--- 🕵️‍♀️ DEBUGGING DATABASE CONNECTION ---")
    
    # 1. Check URI
    uri = app.config.get("SQLALCHEMY_DATABASE_URI")
    print(f"✅ SQLALCHEMY_DATABASE_URI: {uri}")
    
    # Check if file exists at that path
    if uri and uri.startswith("sqlite:///"):
        path = uri.replace("sqlite:///", "")
        # Handle relative paths in URI
        if not os.path.isabs(path):
            path = os.path.join(app.root_path, path)
            
        print(f"📂 Resolved Database Path: {os.path.abspath(path)}")
        if os.path.exists(path):
            print("   -> ✅ File exists.")
        else:
            print("   -> ❌ FILE DOES NOT EXIST AT THIS PATH!")

    with app.app_context():
        # 2. Check Table Info
        print("\n--- 📋 CHECKING TICKETS TABLE ---")
        try:
            # Using text() for safety
            result = db.session.execute(text("PRAGMA table_info(tickets)"))
            columns = [row[1] for row in result] # row[1] is column name
            print(f"Current Columns: {columns}")
            
            if 'ticket_number' in columns:
                print("✅ Column 'ticket_number' ALREADY EXISTS.")
            else:
                print("❌ Column 'ticket_number' MISSING. Attempting to add...")
                
                # 3. Force Add Column
                db.session.execute(text("ALTER TABLE tickets ADD COLUMN ticket_number VARCHAR(20)"))
                db.session.commit()
                print("✅ ALTER TABLE SUCCESS: Column added.")
                
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error inspecting/modifying table: {e}")

if __name__ == "__main__":
    run_debug()