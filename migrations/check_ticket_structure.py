import sqlite3

conn = sqlite3.connect("crm.db")
cursor = conn.cursor()

cursor.execute("PRAGMA table_info(tickets);")

columns = cursor.fetchall()

for col in columns:
    print(col)

conn.close()