from flask import Blueprint, request, jsonify
from extensions import db
from models.crm import Lead
from datetime import datetime

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

    # Split name into first and last name
    name_parts = name.strip().split(" ", 1) if name else ["Visitor", ""]
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else "Unknown"

    # Create a new Lead from the contact form
    new_lead = Lead(
        first_name=first_name,
        last_name=last_name,
        email=email,
        company="Website Inquiry", # Default company for public leads
        source="Website Contact Form",
        created_at=datetime.utcnow()
    )
    db.session.add(new_lead)
    db.session.commit()
    return jsonify({"message": "Contact submitted successfully"}), 201