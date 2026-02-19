import sqlite3

conn = sqlite3.connect("crm.db")
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE leads ADD COLUMN company TEXT")
except Exception as e:
    print("company column may already exist:", e)

try:
    cursor.execute("ALTER TABLE leads ADD COLUMN source TEXT")
except Exception as e:
    print("source column may already exist:", e)

try:
    cursor.execute("ALTER TABLE leads ADD COLUMN ip_address TEXT")
except Exception as e:
    print("ip_address column may already exist:", e)

try:
    cursor.execute("ALTER TABLE leads ADD COLUMN city TEXT")
except Exception as e:
    print("city column may already exist:", e)

try:
    cursor.execute("ALTER TABLE leads ADD COLUMN state TEXT")
except Exception as e:
    print("state column may already exist:", e)

try:
    cursor.execute("ALTER TABLE leads ADD COLUMN country TEXT")
except Exception as e:
    print("country column may already exist:", e)

conn.commit()
conn.close()

print("Leads table updated successfully.")