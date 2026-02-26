import sqlite3
import os

# Get absolute path to crm.db based on script location
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "..", "crm.db")

def fix_missing_table():
    print(f"🔍 Checking database at: {os.path.abspath(DB_PATH)}")
    
    if not os.path.exists(DB_PATH):
        print(f"❌ Error: {DB_PATH} not found.")
        return

    print(f"✅ Connecting to {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='whatsapp_accounts'")
        if cursor.fetchone():
            print("ℹ️ Table 'whatsapp_accounts' already exists.")
        else:
            print("⚠️ Table 'whatsapp_accounts' missing. Creating dummy table to satisfy migration...")
            cursor.execute("CREATE TABLE whatsapp_accounts (id INTEGER PRIMARY KEY, company_id INTEGER, business_id VARCHAR(100))")
            print("✅ Dummy table 'whatsapp_accounts' created successfully.")
            conn.commit()
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    fix_missing_table()