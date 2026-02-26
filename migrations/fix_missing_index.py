import sqlite3
import os

# Get absolute path to crm.db based on script location
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "..", "crm.db")

def fix_missing_index():
    print(f"🔍 Checking database at: {os.path.abspath(DB_PATH)}")
    
    if not os.path.exists(DB_PATH):
        print(f"❌ Error: {DB_PATH} not found.")
        return

    print(f"✅ Connecting to {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check if table exists first, as an index needs a table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='password_reset_tokens'")
        if not cursor.fetchone():
            print("⚠️ Table 'password_reset_tokens' missing. Creating it first...")
            cursor.execute("CREATE TABLE password_reset_tokens (id INTEGER PRIMARY KEY, email VARCHAR(120))")
            print("✅ Dummy table 'password_reset_tokens' created.")

        # Check if the index itself exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='ix_password_reset_tokens_email'")
        if cursor.fetchone():
            print("ℹ️ Index 'ix_password_reset_tokens_email' already exists.")
        else:
            print("⚠️ Index 'ix_password_reset_tokens_email' missing. Creating dummy index...")
            cursor.execute("CREATE INDEX ix_password_reset_tokens_email ON password_reset_tokens (email)")
            print("✅ Dummy index 'ix_password_reset_tokens_email' created successfully.")
            conn.commit()

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    fix_missing_index()