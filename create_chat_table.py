import sqlite3
import os

def create_chat_table():
    db_path = "crm.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("--- 💬 Creating Chat Messages Table ---")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        sender TEXT,
        message TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    conn.commit()
    conn.close()
    print("✅ Chat Messages table created successfully.")

if __name__ == "__main__":
    create_chat_table()