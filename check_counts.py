import sqlite3

conn = sqlite3.connect("crm.db")
cursor = conn.cursor()

cursor.execute("SELECT COUNT(*) FROM leads")
print("Leads:", cursor.fetchone()[0])

cursor.execute("SELECT COUNT(*) FROM deals")
print("Deals:", cursor.fetchone()[0])

cursor.execute("SELECT COUNT(*) FROM activities")
print("Activities:", cursor.fetchone()[0])

conn.close()