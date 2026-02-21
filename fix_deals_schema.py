import sqlite3
import os

def fix_deals_table():
    db_path = "crm.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Database {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("--- 🔧 Fixing Deals Table Schema ---")

    # Get existing columns
    cursor.execute("PRAGMA table_info(deals)")
    columns = [info[1] for info in cursor.fetchall()]
    print(f"Current columns: {columns}")

    # 1. Add 'status' column
    if 'status' not in columns:
        print("Adding 'status' column...")
        try:
            cursor.execute("ALTER TABLE deals ADD COLUMN status TEXT DEFAULT 'open'")
            print("✅ Added 'status' column.")
        except Exception as e:
            print(f"❌ Error adding 'status': {e}")
    else:
        print("ℹ️ 'status' column already exists.")

    # 2. Add 'assigned_to' column (if missing)
    if 'assigned_to' not in columns:
        print("Adding 'assigned_to' column...")
        try:
            cursor.execute("ALTER TABLE deals ADD COLUMN assigned_to TEXT")
            print("✅ Added 'assigned_to' column.")
        except Exception as e:
            print(f"❌ Error adding 'assigned_to': {e}")

    # 3. Update existing records
    print("🔄 Updating existing deals...")
    # Set default status
    cursor.execute("UPDATE deals SET status = 'open' WHERE status IS NULL")
    # Auto-update 'Won' deals based on stage if possible
    cursor.execute("UPDATE deals SET status = 'won' WHERE stage LIKE 'Won%' OR stage LIKE 'Closed Won%'")
    cursor.execute("UPDATE deals SET status = 'lost' WHERE stage LIKE 'Lost%' OR stage LIKE 'Closed Lost%'")

    conn.commit()
    conn.close()
    print("✅ Deals table schema fixed and data updated successfully.")

if __name__ == "__main__":
    fix_deals_table()