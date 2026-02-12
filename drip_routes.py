from flask import Blueprint, request, jsonify
from extensions import db
from routes.auth_routes import token_required
from drip_campaign import DripCampaign, DripStep, DripEnrollment
from models.crm import Lead
from sqlalchemy import func
from datetime import datetime, timedelta

drip_bp = Blueprint('drip_campaigns', __name__, url_prefix="/api/drip-campaigns")

# 1. Campaign CRUD
@drip_bp.route('', methods=['POST'])
@token_required
def create_drip_campaign(current_user):
    data = request.get_json()
    if not data.get('name') or not data.get('audience_type'):
        return jsonify({"error": "Missing required fields: name, audience_type"}), 400

    campaign = DripCampaign(
        name=data['name'],
        audience_type=data['audience_type'],
        audience_value=data.get('audience_value'),
        organization_id=current_user.organization_id
    )
    db.session.add(campaign)
    db.session.commit()
    return jsonify({"message": "Drip campaign created", "id": campaign.id}), 201

@drip_bp.route('', methods=['GET'])
@token_required
def get_drip_campaigns(current_user):
    campaigns = DripCampaign.query.filter_by(organization_id=current_user.organization_id).order_by(DripCampaign.created_at.desc()).all()
    result = [{
        "id": c.id,
        "name": c.name,
        "status": c.status,
        "audience_type": c.audience_type,
        "audience_value": c.audience_value,
        "created_at": c.created_at.isoformat()
    } for c in campaigns]
    return jsonify(result)

@drip_bp.route('/<int:campaign_id>', methods=['PUT'])
@token_required
def update_drip_campaign(current_user, campaign_id):
    campaign = DripCampaign.query.filter_by(id=campaign_id, organization_id=current_user.organization_id).first_or_404()
    data = request.get_json()

    campaign.name = data.get('name', campaign.name)
    campaign.audience_type = data.get('audience_type', campaign.audience_type)
    campaign.audience_value = data.get('audience_value', campaign.audience_value)
    
    db.session.commit()
    return jsonify({"message": "Drip campaign updated"}), 200

@drip_bp.route('/<int:campaign_id>', methods=['DELETE'])
@token_required
def delete_drip_campaign(current_user, campaign_id):
    campaign = DripCampaign.query.filter_by(id=campaign_id, organization_id=current_user.organization_id).first_or_404()
    
    db.session.delete(campaign)
    db.session.commit()
    return jsonify({"message": "Drip campaign deleted"}), 200

# 2. Steps API
@drip_bp.route('/<int:campaign_id>/steps', methods=['POST'])
@token_required
def add_drip_step(current_user, campaign_id):
    campaign = DripCampaign.query.filter_by(id=campaign_id, organization_id=current_user.organization_id).first_or_404()
    data = request.get_json()

    if not data.get('subject') or not data.get('body'):
        return jsonify({"error": "Missing required fields: subject, body"}), 400

    last_step = DripStep.query.filter_by(campaign_id=campaign_id).order_by(DripStep.step_number.desc()).first()
    step_number = (last_step.step_number + 1) if last_step else 1

    step = DripStep(
        campaign_id=campaign_id,
        step_number=step_number,
        delay_days=data.get('delay_days', 0),
        subject=data['subject'],
        body=data['body']
    )
    db.session.add(step)
    db.session.commit()
    return jsonify({"message": "Drip step added", "id": step.id}), 201

@drip_bp.route('/<int:campaign_id>/steps', methods=['GET'])
@token_required
def get_drip_steps(current_user, campaign_id):
    DripCampaign.query.filter_by(id=campaign_id, organization_id=current_user.organization_id).first_or_404()
    steps = DripStep.query.filter_by(campaign_id=campaign_id).order_by(DripStep.step_number.asc()).all()
    result = [{
        "id": s.id,
        "step_number": s.step_number,
        "delay_days": s.delay_days,
        "subject": s.subject,
        "created_at": s.created_at.isoformat()
    } for s in steps]
    return jsonify(result)

# 3. Activate / Pause API
def enroll_leads(campaign):
    first_step = DripStep.query.filter_by(campaign_id=campaign.id, step_number=1).first()
    if not first_step:
        return

    leads_query = Lead.query.filter_by(organization_id=campaign.organization_id, is_deleted=False)
    if campaign.audience_type == 'all':
        pass
    elif campaign.audience_type == 'tag' and campaign.audience_value:
        # Using 'source' as a proxy for tags as 'tags' field doesn't exist on Lead model
        leads_query = leads_query.filter(Lead.source == campaign.audience_value)
    elif campaign.audience_type == 'new_leads':
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        leads_query = leads_query.filter(Lead.created_at >= seven_days_ago)
    else:
        return

    for lead in leads_query.all():
        if DripEnrollment.query.filter_by(campaign_id=campaign.id, lead_id=lead.id).first():
            continue

        delay = timedelta(days=first_step.delay_days)
        next_send_at = datetime.utcnow() + delay

        enrollment = DripEnrollment(
            campaign_id=campaign.id,
            lead_id=lead.id,
            next_send_at=next_send_at
        )
        db.session.add(enrollment)

@drip_bp.route('/<int:campaign_id>/activate', methods=['POST'])
@token_required
def activate_drip_campaign(current_user, campaign_id):
    campaign = DripCampaign.query.filter_by(id=campaign_id, organization_id=current_user.organization_id).first_or_404()
    
    if not campaign.steps:
        return jsonify({"error": "Cannot activate a campaign with no steps"}), 400

    campaign.status = 'active'
    enroll_leads(campaign)
    
    db.session.commit()
    return jsonify({"message": "Campaign activated and leads enrolled"}), 200

@drip_bp.route('/<int:campaign_id>/pause', methods=['POST'])
@token_required
def pause_drip_campaign(current_user, campaign_id):
    campaign = DripCampaign.query.filter_by(id=campaign_id, organization_id=current_user.organization_id).first_or_404()
    campaign.status = 'paused'
    
    DripEnrollment.query.filter_by(campaign_id=campaign.id, status='active').update({"status": "stopped"})
    
    db.session.commit()
    return jsonify({"message": "Campaign paused and enrollments stopped"}), 200