from flask import Blueprint, request, jsonify
from extensions import db
from models.crm import Lead

website_bp = Blueprint("website", __name__)

@website_bp.route("/")
def index():
    return jsonify({"message": "CRM Backend API is running"})

@website_bp.route("/features")
def features():
    return jsonify({
        "plans": [
            {"name": "Free", "price": "$0/mo", "features": ["10 Users", "2 GB Storage"]},
            {"name": "Pro", "price": "$15/mo", "features": ["Unlimited Users", "10 GB Storage"]}
        ]
    })

@website_bp.route("/contact", methods=["POST"])
def contact():
    data = request.get_json()
    name = data.get("name")
    email = data.get("email")
    message = data.get("message")

    # Create a new Lead from the contact form
    new_lead = Lead(
        name=name,
        email=email,
        description=message,
        source="Website Contact Form"
    )
    db.session.add(new_lead)
    db.session.commit()
    return jsonify({"message": "Contact submitted successfully"}), 201