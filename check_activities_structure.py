import sqlite3

conn = sqlite3.connect("crm.db")
cursor = conn.cursor()

cursor.execute("PRAGMA table_info(activities)")
columns = cursor.fetchall()

print("Activities Table Structure:\n")
for col in columns:
    print(col)

conn.close()