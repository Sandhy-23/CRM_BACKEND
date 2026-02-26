import sqlite3
import os

# Path to your database file
DB_PATH = "../crm.db"

def fix_automations():
    print(f"🔍 Checking database at: {os.path.abspath(DB_PATH)}")
    
    if not os.path.exists(DB_PATH):
        print(f"❌ Error: {DB_PATH} not found. Make sure you are running this from the 'migrations' folder or adjust DB_PATH.")
        return

    print(f"✅ Connecting to {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check if automations table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='automations'")
        if not cursor.fetchone():
            print("⚠️ Table 'automations' does not exist. Skipping.")
            return

        # Check if column exists
        cursor.execute("PRAGMA table_info(automations)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if "status" in columns:
            print("ℹ️ Column 'status' already exists in 'automations' table.")
        else:
            print("⚠️ Column 'status' missing. Adding it now...")
            cursor.execute("ALTER TABLE automations ADD COLUMN status VARCHAR(50) DEFAULT 'active'")
            print("✅ Column 'status' added successfully.")
            conn.commit()

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    fix_automations()