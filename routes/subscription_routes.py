from flask import Blueprint, request, jsonify
from models.subscription import Subscription
from extensions import db
from datetime import datetime

subscription_bp = Blueprint("subscription_bp", __name__)


# Get subscription status
@subscription_bp.route("/api/subscription/status/<int:org_id>", methods=["GET"])
def get_subscription_status(org_id):

    sub = Subscription.query.filter_by(organization_id=org_id).first()

    if not sub:
        return jsonify({"message": "Subscription not found"}), 404

    return jsonify({
        "organization_id": sub.organization_id,
        "plan_id": sub.plan_id,
        "status": sub.status,
        "is_trial": sub.is_trial,
        "start_date": sub.start_date,
        "end_date": sub.end_date
    })


# Create subscription
@subscription_bp.route("/api/subscription/create", methods=["POST"])
def create_subscription():

    data = request.get_json()

    new_sub = Subscription(
        organization_id=data["organization_id"],
        plan_id=data.get("plan_id"),
        start_date=datetime.utcnow(),
        end_date=data.get("end_date"),
        status="active",
        is_trial=data.get("is_trial", False)
    )

    db.session.add(new_sub)
    db.session.commit()

    return jsonify({
        "message": "Subscription created successfully"
    })