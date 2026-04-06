import mysql.connector

def get_pipeline(value, lead_source):
    if lead_source in ['Partner', 'Referral']:
        return 'Partnership'
    elif value >= 1000000:
        return 'Enterprise'
    else:
        return 'Sales'


conn = mysql.connector.connect(
    host="127.0.0.1",
    user="root",
    password="1234",
    database="crm_db"   # updated to your actual database name
)

cursor = conn.cursor(dictionary=True)

cursor.execute("SELECT id, value, lead_source FROM deals")
deals = cursor.fetchall()

for deal in deals:
    pipeline = get_pipeline(deal['value'], deal['lead_source'])

    cursor.execute(
        "UPDATE deals SET pipeline = %s WHERE id = %s",
        (pipeline, deal['id'])
    )

conn.commit()
cursor.close()
conn.close()

print("✅ Pipelines updated successfully")