from app import app
from extensions import db
from models.payment import Payment
from sqlalchemy.exc import OperationalError

def check_and_create_payment_table():
    with app.app_context():
        print("--- 🔍 Checking Payment Table ---")
        try:
            # Try to query the table
            payments = Payment.query.all()
            print(f"✅ Table 'payments' exists. Current records: {payments}")
        except OperationalError as e:
            print(f"⚠️ Table 'payments' not found (Error: {e}). Creating it now...")
            # Create the table
            db.create_all()
            print("✅ Table 'payments' created successfully.")

if __name__ == "__main__":
    check_and_create_payment_table()