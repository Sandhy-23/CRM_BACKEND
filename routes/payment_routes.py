from flask import Blueprint, request, jsonify
from extensions import db
from models.payment_link import PaymentLink
from routes.auth_routes import token_required
import requests
import os

payment_bp = Blueprint('payment', __name__, url_prefix='/api')

@payment_bp.route("/create-payment-link", methods=["POST"])
@token_required
def create_payment_link(current_user):
    data = request.json

    # Get credentials from environment variables
    client_id = os.getenv("CASHFREE_APP_ID")
    client_secret = os.getenv("CASHFREE_SECRET_KEY")
    api_version = "2022-09-01"
    cashfree_url = "https://api.cashfree.com/pg/links"

    if not client_id or not client_secret:
        return jsonify({"error": "Payment gateway is not configured on the server."}), 500

    payload = {
        "link_amount": data["link_amount"],
        "link_currency": data["link_currency"],
        "link_purpose": data["link_purpose"],
        "customer_details": data["customer_details"],
        "link_notify": {
            "send_email": True
        }
    }

    headers = {
        "x-client-id": client_id,
        "x-client-secret": client_secret,
        "x-api-version": api_version,
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(cashfree_url, json=payload, headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        result = response.json()

        # Store the successful payment link details in the database
        customer_details = data.get("customer_details", {})
        new_payment = PaymentLink(
            link_id=result.get("link_id"),
            customer_name=customer_details.get("customer_name"),
            customer_email=customer_details.get("customer_email"),
            customer_phone=customer_details.get("customer_phone"),
            amount=data.get("link_amount"),
            currency=data.get("link_currency"),
            purpose=data.get("link_purpose"),
            payment_link=result.get("link_url"),
            qr_code=result.get("link_qrcode"),
            status=result.get("link_status", "CREATED")
        )
        db.session.add(new_payment)
        db.session.commit()

        return jsonify(result), 200

    except requests.exceptions.RequestException as e:
        error_details = str(e)
        if e.response is not None:
            error_details = e.response.json() if e.response.content else e.response.text
        return jsonify({"error": "Failed to communicate with payment gateway", "details": error_details}), 502
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "An internal server error occurred", "details": str(e)}), 500