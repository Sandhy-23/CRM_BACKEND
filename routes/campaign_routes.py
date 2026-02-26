from flask import Blueprint, request, jsonify
from extensions import db
from models.campaign import Campaign
from routes.auth_routes import token_required
from datetime import datetime

campaign_bp = Blueprint('campaigns', __name__, url_prefix="/api/campaigns")

def serialize_campaign(c):
    return {
        "id": c.id,
        "name": c.name,
        "channel": c.channel,
        "status": c.status,
        "color": c.color,
        "month": c.month,
        "year": c.year,
        "config": c.config,
        "whatsappConfig": c.whatsapp_config,
        "branch": c.branch,
        "createdAt": c.created_at.isoformat() if c.created_at else None,
        "updatedAt": c.updated_at.isoformat() if c.updated_at else None
    }

@campaign_bp.route('', methods=['GET'])
@token_required
def get_campaigns(current_user):
    query = Campaign.query.filter_by(organization_id=current_user.organization_id)

    month = request.args.get("month")
    year = request.args.get("year")
    channel = request.args.get("channel")
    status = request.args.get("status")
    branch = request.args.get("branch")

    if month:
        query = query.filter_by(month=int(month))
    if year:
        query = query.filter_by(year=int(year))
    if channel:
        query = query.filter_by(channel=channel)
    if status:
        query = query.filter_by(status=status)
    if branch:
        query = query.filter_by(branch=branch)

    campaigns = query.order_by(Campaign.created_at.desc()).all()
    return jsonify([serialize_campaign(c) for c in campaigns]), 200

@campaign_bp.route('', methods=['POST'])
@token_required
def create_campaign(current_user):
    data = request.get_json()
    
    new_campaign = Campaign(
        name=data["name"],
        channel=data["channel"],
        status=data.get("status", "Draft"),
        month=data.get("month"),
        year=data.get("year"),
        branch=data.get("branch"),
        whatsapp_config=data.get("whatsappConfig"),
        organization_id=current_user.organization_id,
        created_by=current_user.id
    )

    db.session.add(new_campaign)
    db.session.commit()

    return jsonify(serialize_campaign(new_campaign)), 201

@campaign_bp.route('/<string:campaign_id>/status', methods=['PATCH'])
@token_required
def update_status(current_user, campaign_id):
    campaign = Campaign.query.filter_by(id=campaign_id, organization_id=current_user.organization_id).first_or_404()
    campaign.status = request.json["status"]
    db.session.commit()
    return jsonify({"message": "Status updated"})

@campaign_bp.route('/<string:campaign_id>/config', methods=['PUT'])
@token_required
def save_config(current_user, campaign_id):
    campaign = Campaign.query.filter_by(id=campaign_id, organization_id=current_user.organization_id).first_or_404()
    campaign.config = request.json["config"]
    campaign.status = "Running"
    db.session.commit()
    return jsonify(serialize_campaign(campaign))