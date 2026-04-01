from flask import Blueprint, request, jsonify
from extensions import db
from models.campaign import Campaign
from models.campaign_log import CampaignLog
from routes.auth_routes import token_required
from datetime import datetime

campaign_bp = Blueprint('campaigns', __name__)

@campaign_bp.route('/api/campaigns', methods=['GET'])
def get_campaigns():
    # Simplified for MVP: No auth for now if causing issues, or add @token_required
    try:
        status = request.args.get('status')
        channel = request.args.get('channel')
        
        query = Campaign.query
        if status:
            query = query.filter_by(status=status)
        if channel:
            query = query.filter_by(channel=channel)
            
        campaigns = query.order_by(Campaign.created_at.desc()).all()
        
        return jsonify([{
            "id": c.id,
            "name": c.name,
            "channel": c.channel,
            "status": c.status,
            "scheduled_at": c.scheduled_at.isoformat() if c.scheduled_at else None,
            "created_at": c.created_at.isoformat()
        } for c in campaigns]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@campaign_bp.route('/api/campaigns', methods=['POST'])
@campaign_bp.route('/api/campaign/create', methods=['POST'])
def create_campaign():
    try:
        data = request.get_json()
        new_campaign = Campaign(
            name=data.get('name'),
            channel=data.get('channel'),
            status='Draft',
            # config=data.get('config'), # Requires JSON type in model
            organization_id=1 # Default
        )
        db.session.add(new_campaign)
        db.session.commit()
        
        return jsonify({"message": "Campaign created", "campaign_id": new_campaign.id}), 201
    except Exception as e:
        print(f"❌ Error creating campaign: {e}")
        return jsonify({"error": str(e)}), 500

@campaign_bp.route('/api/campaign/dashboard', methods=['GET'])
def get_campaign_dashboard():
    try:
        total = Campaign.query.count()
        active = Campaign.query.filter_by(status='Running').count()
        completed = Campaign.query.filter_by(status='Completed').count()
        
        return jsonify({
            "total": total,
            "active": active,
            "completed": completed
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@campaign_bp.route('/api/campaign/update/<string:campaign_id>', methods=['PUT', 'DELETE'])
def update_campaign_status(campaign_id):
    try:
        campaign = Campaign.query.get(campaign_id)
        if not campaign:
            return jsonify({"error": "Campaign not found"}), 404
            
        data = request.get_json()
        
        if request.method == 'DELETE':
            db.session.delete(campaign)
            db.session.commit()
            return jsonify({"message": "Campaign deleted"}), 200

        if 'status' in data:
            campaign.status = data['status']
            
        if 'name' in data:
            campaign.name = data['name']

        db.session.commit()
        return jsonify({"message": "Campaign updated", "status": campaign.status}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500