import sqlite3
import os

def inspect_database():
    # Check common locations for the database file
    possible_paths = ['crm.db', 'instance/crm.db']
    db_path = None

    for path in possible_paths:
        if os.path.exists(path):
            db_path = path
            break
    
    if not db_path:
        print("❌ Database file 'crm.db' not found in current or 'instance' directory.")
        return

    print(f"✅ Connecting to database: {db_path}")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # --- Inspect Calendar Events ---
        print("\n--- Table: calendar_event ---")
        try:
            cursor.execute("PRAGMA table_info(calendar_event)")
            columns = cursor.fetchall()
            col_names = [col[1] for col in columns]
            print(f"Columns: {col_names}")

            cursor.execute("SELECT id, title, created_by FROM calendar_event")
            rows = cursor.fetchall()
            if not rows:
                print("No data found in calendar_event table.")
            else:
                print("Data (id, title, created_by):")
                for row in rows:
                    print(row)
        except sqlite3.OperationalError:
            print("Table 'calendar_event' not found.")

        # --- Inspect Reminders ---
        print("\n--- Table: reminder ---")
        try:
            cursor.execute("PRAGMA table_info(reminder)")
            columns = cursor.fetchall()
            col_names = [col[1] for col in columns]
            print(f"Columns: {col_names}")
            
            cursor.execute("SELECT id, event_id, remind_at, is_sent, user_id FROM reminder")
            rows = cursor.fetchall()
            if not rows:
                print("No data found in reminder table.")
            else:
                print("Data (id, event_id, remind_at, is_sent, user_id):")
                for row in rows:
                    print(row)
        except sqlite3.OperationalError:
            print("Table 'reminder' not found.")
            
        # --- Inspect Users ---
        print("\n--- Table: users ---")
        try:
            cursor.execute("PRAGMA table_info(users)")
            columns = cursor.fetchall()
            col_names = [col[1] for col in columns]
            print(f"Columns: {col_names}")

            # Fetch only relevant columns for this debug task
            cursor.execute("SELECT id, email, role, organization_id FROM users")
            rows = cursor.fetchall()
            if not rows:
                print("No data found in users table.")
            else:
                print("Data (id, email, role, organization_id):")
                for row in rows:
                    print(row)
        except sqlite3.OperationalError:
            print("Table 'users' not found.")

        conn.close()
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    inspect_database()