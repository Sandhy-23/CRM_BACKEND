from flask import Blueprint, request, jsonify
from extensions import db
from models.campaign import Campaign
from models.campaign_log import CampaignLog
from routes.auth_routes import token_required
from datetime import datetime

campaign_bp = Blueprint("campaign", __name__, url_prefix="/api/campaign")

@campaign_bp.route("/create", methods=["POST"])
@token_required
def create_campaign(current_user):
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON body provided"}), 400

    name = data.get("name")
    if not name:
        return jsonify({"error": "Campaign name is required"}), 400

    month_value = data.get("month")

    # As per your instruction, handle both month name and number
    if isinstance(month_value, str):
        month_map = {
            "January": 1, "February": 2, "March": 3, "April": 4,
            "May": 5, "June": 6, "July": 7, "August": 8,
            "September": 9, "October": 10, "November": 11, "December": 12
        }
        # Use .get() for safety, returns None if not found
        month_value = month_map.get(month_value.capitalize())

    # After conversion, if month is still not a valid number, you could add another check
    if month_value is None or not isinstance(month_value, int):
        return jsonify({"error": "A valid month (name or number) is required"}), 400

    campaign = Campaign(
        name=name,
        channel=data.get("channel"),
        status=data.get("status"),
        month=month_value,
        year=data.get("year"),
        color=data.get("color"),
        created_by=current_user.id,
        organization_id=current_user.organization_id
    )
    db.session.add(campaign)
    db.session.commit()
    return jsonify({
        "message": "Campaign created successfully",
        "campaign_id": campaign.id
    }), 201

@campaign_bp.route("/whatsapp-config/<int:id>", methods=["POST"])
@token_required
def save_whatsapp_config(current_user, id):
    campaign = Campaign.query.get(id)
    data = request.json
    campaign.whatsapp_config = {
        "message_type": data.get("message_type"),
        "audience": data.get("audience"),
        "message": data.get("message")
    }
    db.session.commit()
    return jsonify({"message": "Configuration saved"})

@campaign_bp.route("/schedule/<int:id>", methods=["POST"])
@token_required
def schedule_campaign(current_user, id):
    campaign = Campaign.query.get(id)
    data = request.json
    campaign.scheduled_at = datetime.strptime(
        data.get("scheduled_at"),
        "%Y-%m-%d %H:%M:%S"
    )
    campaign.status = "Scheduled"
    db.session.commit()
    return jsonify({"message": "Campaign scheduled"})

@campaign_bp.route("/send/<int:id>", methods=["POST"])
@token_required
def send_campaign(current_user, id):
    campaign = Campaign.query.get(id)
    # Mock contact list as per plan
    contacts = [1, 2, 3, 4]
    for contact in contacts:
        log = CampaignLog(
            campaign_id=id,
            contact_id=contact,
            status="sent",
            channel=campaign.channel
        )
        db.session.add(log)
    campaign.status = "Running"
    db.session.commit()
    return jsonify({"message": "Campaign sent"})

@campaign_bp.route("/list", methods=["GET"])
@token_required
def get_campaigns(current_user):
    campaigns = Campaign.query.filter_by(organization_id=current_user.organization_id).all()
    result = []
    for c in campaigns:
        result.append({
            "id": c.id,
            "name": c.name,
            "channel": c.channel,
            "status": c.status,
            "month": c.month,
            "year": c.year
        })
    return jsonify(result)

@campaign_bp.route("/stats/<int:id>")
@token_required
def campaign_stats(current_user, id):
    sent = CampaignLog.query.filter_by(campaign_id=id).count()
    opened = CampaignLog.query.filter_by(
        campaign_id=id,
        opened=True
    ).count()
    clicked = CampaignLog.query.filter_by(
        campaign_id=id,
        clicked=True
    ).count()
    return jsonify({
        "sent": sent,
        "opened": opened,
        "clicked": clicked
    })