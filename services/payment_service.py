import requests
import os
import uuid

# Load environment variables
CASHFREE_APP_ID = os.getenv("CASHFREE_APP_ID")
CASHFREE_SECRET_KEY = os.getenv("CASHFREE_SECRET_KEY")
CASHFREE_API_URL = os.getenv("CASHFREE_API_URL", "https://sandbox.cashfree.com/pg")
FRONTEND_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:3000")

def create_cashfree_order(customer_id, customer_email, customer_phone, amount):
    """
    Creates a payment order using Cashfree Orders API.
    Returns the checkout link (pointing to our frontend) and order_id.
    """
    try:
        # Generate a unique order ID
        order_id = f"order_{uuid.uuid4().hex[:12]}"
        
        # Ensure phone is valid for Cashfree (min 10 chars), else use dummy
        phone = customer_phone if customer_phone and len(str(customer_phone)) >= 10 else "9999999999"

        payload = {
            "order_id": order_id,
            "order_amount": float(amount),
            "order_currency": "INR",
            "customer_details": {
                "customer_id": str(customer_id),
                "customer_email": customer_email,
                "customer_phone": phone
            },
            "order_meta": {
                # Where Cashfree should redirect after payment on the frontend
                "return_url": f"{FRONTEND_URL}/payment/status?order_id={order_id}"
            }
        }

        headers = {
            "x-client-id": CASHFREE_APP_ID,
            "x-client-secret": CASHFREE_SECRET_KEY,
            "x-api-version": "2023-08-01",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        response = requests.post(f"{CASHFREE_API_URL}/orders", json=payload, headers=headers)
        data = response.json()

        if response.status_code in [200, 201]:
            checkout_url = f"{FRONTEND_URL}/checkout/{order_id}"
            return checkout_url, order_id
        else:
            print(f"[FAIL] Cashfree Order Creation Failed: {data}")
            return None, None

    except Exception as e:
        print(f"[FAIL] Cashfree Exception: {str(e)}")
        return None, None