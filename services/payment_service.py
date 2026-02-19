import razorpay
import os

client = razorpay.Client(
    auth=(os.getenv("RAZORPAY_KEY_ID"), os.getenv("RAZORPAY_KEY_SECRET"))
)

def create_payment_link(amount, email):
    """
    Creates a Razorpay payment link.
    """
    try:
        payment_link = client.payment_link.create({
            "amount": amount * 100,
            "currency": "INR",
            "description": "CRM Subscription Payment",
            "customer": {
                "email": email
            }
        })

        return payment_link["short_url"], payment_link["id"]
    except Exception as e:
        print(f"[FAIL] Razorpay payment link creation failed: {e}")
        return None, None