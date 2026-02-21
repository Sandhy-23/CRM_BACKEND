import sqlite3
import os

def fix_users_table():
    db_path = "crm.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Database {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("--- 🔧 Fixing Users Table Schema ---")

    # Get existing columns
    cursor.execute("PRAGMA table_info(users)")
    columns = [info[1] for info in cursor.fetchall()]
    print(f"Current columns: {columns}")

    # 1. Add 'target' column
    if 'target' not in columns:
        print("Adding 'target' column...")
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN target FLOAT DEFAULT 0")
            print("✅ Added 'target' column.")
        except Exception as e:
            print(f"❌ Error adding 'target': {e}")
    else:
        print("ℹ️ 'target' column already exists.")

    # 2. Update Targets for known users
    print("🔄 Updating user targets...")
    updates = [
        ('Ravi Teja', 1500000),
        ('Anu S', 1200000),
        ('Varshini K', 1000000)
    ]
    
    for name, target in updates:
        cursor.execute("UPDATE users SET target = ? WHERE name = ?", (target, name))
        if cursor.rowcount > 0:
            print(f"   -> Updated target for {name}")

    conn.commit()
    conn.close()
    print("✅ Users table schema fixed and data updated successfully.")

if __name__ == "__main__":
    fix_users_table()