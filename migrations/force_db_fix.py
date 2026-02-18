import sqlite3
import os

# Path to your database file
DB_PATH = "crm.db"

def fix_database():
    print(f"🔍 Checking database at: {os.path.abspath(DB_PATH)}")
    
    if not os.path.exists(DB_PATH):
        print(f"❌ Error: {DB_PATH} not found in current directory.")
        return

    print(f"✅ Connecting to {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(tickets)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if "ticket_number" in columns:
            print("ℹ️ Column 'ticket_number' already exists in 'tickets' table.")
        else:
            print("⚠️ Column 'ticket_number' missing. Adding it now...")
            # This is the SQL command equivalent to what you'd run in DB Browser
            cursor.execute("ALTER TABLE tickets ADD COLUMN ticket_number VARCHAR(20)")
            print("✅ Column 'ticket_number' added successfully.")

        # Update NULL values so existing tickets have a number
        print("🔄 Updating NULL ticket numbers...")
        cursor.execute("UPDATE tickets SET ticket_number = 'TKT-' || id WHERE ticket_number IS NULL")
        conn.commit()
        print("💾 Changes saved.")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    fix_database()