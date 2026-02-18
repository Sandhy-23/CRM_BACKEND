import sqlite3
import os

db_path = "crm.db"

if not os.path.exists(db_path):
    print(f"⚠️  WARNING: {db_path} not found in current directory.")
    # Fallback for some Flask configurations
    if os.path.exists(os.path.join("instance", db_path)):
        db_path = os.path.join("instance", db_path)
        print(f"👉 Found database in: {db_path}")

print(f"🔌 Connecting to: {db_path}")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("\n🔨 Checking and adding ALL missing columns to 'tickets' table...")

# List of all columns that should be in the tickets table (besides id and subject)
columns_to_add = [
    ("ticket_number", "TEXT"),
    ("description", "TEXT"),
    ("contact_id", "INTEGER"),
    ("assigned_to", "INTEGER"),
    ("priority", "TEXT"),
    ("status", "TEXT"),
    ("category", "TEXT"),
    ("sla_due_at", "DATETIME"),
    ("organization_id", "INTEGER"),
    ("created_at", "DATETIME"),
    ("updated_at", "DATETIME"),
    ("closed_at", "DATETIME")
]

for col_name, col_type in columns_to_add:
    try:
        cursor.execute(f"ALTER TABLE tickets ADD COLUMN {col_name} {col_type}")
        print(f"   -> Added column: {col_name}")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e):
            print(f"   -> Skipped {col_name} (already exists).")
        else:
            print(f"   -> Error adding {col_name}: {e}")

# Create ticket_comments table
print("\n🔨 Checking 'ticket_comments' table...")
try:
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ticket_comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        comment TEXT NOT NULL,
        is_internal BOOLEAN DEFAULT 0,
        created_at DATETIME,
        FOREIGN KEY (ticket_id) REFERENCES tickets(id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)
    print("   -> 'ticket_comments' table checked/created.")
except Exception as e:
    print(f"   -> Error creating table: {e}")

conn.commit()

# Verification
print("\n🔍 Verifying 'tickets' table structure...")
cursor.execute("PRAGMA table_info(tickets)")
final_columns = [row[1] for row in cursor.fetchall()]
print(f"   Final columns found: {final_columns}")

print("\n🔍 Verifying 'ticket_comments' table structure...")
cursor.execute("PRAGMA table_info(ticket_comments)")
comment_columns = [row[1] for row in cursor.fetchall()]
print(f"   Final columns found: {comment_columns}")

conn.close()

print("\n✅ DONE FIXING TABLE")