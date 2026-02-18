import sqlite3

conn = sqlite3.connect("crm.db")
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE tickets ADD COLUMN ticket_number TEXT;")
    print("Column 'ticket_number' added successfully.")
except Exception as e:
    print("Error:", e)

conn.commit()
conn.close()

print("Done.")