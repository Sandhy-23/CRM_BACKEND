from flask import Blueprint, request, jsonify
from extensions import db
from models.crm import Deal
from models.user import User
from models.pipeline import Pipeline, PipelineStage
from routes.auth_routes import token_required
from datetime import datetime, date
from sqlalchemy import func
from models.activity_logger import log_activity
from models.automation_engine import run_automation_rules

deal_bp = Blueprint('deals', __name__)

def get_deal_query(current_user):
    """Enforce Role Based Access Control for Deals"""
    query = Deal.query.filter_by(organization_id=current_user.organization_id)

    if current_user.role in ['SUPER_ADMIN', 'ADMIN']:
        return query
    
    if current_user.role == 'MANAGER':
        # Manager sees own deals + team deals
        team_ids = [u.id for u in User.query.filter_by(organization_id=current_user.organization_id, department=current_user.department).all()]
        return query.filter(Deal.owner_id.in_(team_ids))
    
    # Employee/User sees only their own deals
    return query.filter_by(owner_id=current_user.id)

@deal_bp.route('/api/deals', methods=['POST'])
@token_required
def create_deal(current_user):
    data = request.get_json()
    
    if not data.get('title') or not data.get('amount'):
        return jsonify({'message': 'Title and Amount are required'}), 400

    # Parse expected_close_date
    expected_date = None
    if data.get('expected_close_date'):
        try:
            expected_date = datetime.strptime(data.get('expected_close_date'), '%Y-%m-%d').date()
        except ValueError:
            pass

    # Pipeline Logic
    pipeline_id = data.get('pipeline_id')
    stage_id = data.get('stage_id')
    
    # If no pipeline provided, fetch default
    if not pipeline_id:
        default_pipeline = Pipeline.query.filter_by(company_id=current_user.organization_id, is_default=True).first()
        if default_pipeline:
            pipeline_id = default_pipeline.id
    
    # If no stage provided, fetch first stage of pipeline
    stage_name = "Prospecting" # Fallback
    if pipeline_id and not stage_id:
        first_stage = PipelineStage.query.filter_by(pipeline_id=pipeline_id).order_by(PipelineStage.stage_order).first()
        if first_stage:
            stage_id = first_stage.id
            stage_name = first_stage.name
    elif stage_id:
        stage = PipelineStage.query.get(stage_id)
        if stage: stage_name = stage.name

    new_deal = Deal(
        title=data['title'],
        amount=data.get('amount', 0),
        lead_id=data.get('lead_id'),
        expected_close_date=expected_date,
        owner_id=current_user.id,
        organization_id=current_user.organization_id,
        stage=stage_name,
        status="Open",
        pipeline_id=pipeline_id,
        stage_id=stage_id
    )
    
    db.session.add(new_deal)
    db.session.commit()

    log_activity(
        module="deal",
        action="created",
        description=f"Deal '{new_deal.title}' created with amount {new_deal.amount}.",
        related_id=new_deal.id)
    
    # --- AUTOMATION TRIGGER ---
    run_automation_rules(
        module="deal",
        trigger_event="deal_created",
        record=new_deal,
        company_id=current_user.organization_id,
        user_id=current_user.id
    )
    return jsonify({'message': 'Deal created successfully', 'deal_id': new_deal.id}), 201

@deal_bp.route('/api/deals', methods=['GET'])
@token_required
def get_deals(current_user):
    query = get_deal_query(current_user)
    deals = query.order_by(Deal.created_at.desc()).all()
    
    return jsonify([
        {
            "id": d.id,
            "title": d.title,
            "amount": d.amount,
            "stage": d.stage,
            "status": d.status,
            "expected_close_date": str(d.expected_close_date) if d.expected_close_date else None,
            "pipeline_id": getattr(d, 'pipeline_id', None),
            "stage_id": getattr(d, 'stage_id', None)
        }
        for d in deals
    ]), 200

@deal_bp.route('/api/deals/<int:deal_id>/stage', methods=['PUT'])
@token_required
def update_stage(current_user, deal_id):
    deal = get_deal_query(current_user).filter_by(id=deal_id).first()
    if not deal:
        return jsonify({'message': 'Deal not found'}), 404

    data = request.get_json()
    
    if 'stage_id' in data:
        stage_id = data['stage_id']
        stage = PipelineStage.query.filter_by(id=stage_id).first()
        
        if not stage:
            return jsonify({'message': 'Stage not found'}), 404
            
        deal.stage_id = stage_id
        deal.stage = stage.name # Sync legacy field
        
        # Auto-update status
        if stage.name.lower() == 'won': deal.status = 'Won'
        elif stage.name.lower() == 'lost': deal.status = 'Lost'
        
        db.session.commit()
        log_activity(
            module="deal",
            action="stage_updated",
            description=f"Deal '{deal.title}' moved to stage '{stage.name}'.",
            related_id=deal.id
        )

        # --- AUTOMATION TRIGGER ---
        run_automation_rules(
            module="deal",
            trigger_event="deal_updated",
            record=deal,
            company_id=current_user.organization_id,
            user_id=current_user.id
        )
        return jsonify({'message': 'Deal stage updated'}), 200
        
    return jsonify({'message': 'Stage is required'}), 400

@deal_bp.route('/api/deals/<int:deal_id>/close', methods=['PUT'])
@token_required
def close_deal(current_user, deal_id):
    deal = get_deal_query(current_user).filter_by(id=deal_id).first()
    if not deal:
        return jsonify({'message': 'Deal not found'}), 404

    data = request.get_json()
    status = data.get('status')
    
    if status not in ['Won', 'Lost']:
        return jsonify({'message': 'Status must be Won or Lost'}), 400

    deal.status = status
    deal.stage = status # Sync stage with status for Won/Lost
    db.session.commit()
    log_activity(
        module="deal",
        action="status_updated",
        description=f"Deal '{deal.title}' status changed to '{status}'.",
        related_id=deal.id
    )

    # --- AUTOMATION TRIGGER ---
    run_automation_rules(
        module="deal",
        trigger_event="deal_updated",
        record=deal,
        company_id=current_user.organization_id,
        user_id=current_user.id
    )
    return jsonify({'message': 'Deal closed successfully'}), 200

@deal_bp.route('/api/deals/<int:deal_id>/close', methods=['POST'])
@token_required
def close_deal_with_outcome(current_user, deal_id):
    deal = get_deal_query(current_user).filter_by(id=deal_id).first()
    if not deal:
        return jsonify({'message': 'Deal not found'}), 404

    data = request.get_json()
    outcome = data.get('outcome')
    reason = data.get('reason')

    if outcome not in ['WON', 'LOST']:
        return jsonify({'message': 'Outcome must be WON or LOST'}), 400

    deal.outcome = outcome
    deal.closed_at = datetime.utcnow()

    if outcome == 'WON':
        deal.status = 'Won' # Sync with legacy status
        deal.stage = 'Won'
        deal.win_reason = reason
        deal.loss_reason = None
    else:
        deal.status = 'Lost' # Sync with legacy status
        deal.stage = 'Lost'
        deal.loss_reason = reason
        deal.win_reason = None

    db.session.commit()

    log_activity(
        module="deal",
        action="closed",
        description=f"Deal '{deal.title}' closed as {outcome}.",
        related_id=deal.id
    )
    # --- AUTOMATION TRIGGER ---
    run_automation_rules(
        module="deal",
        trigger_event="deal_updated",
        record=deal,
        company_id=current_user.organization_id,
        user_id=current_user.id
    )
    return jsonify({'message': f'Deal marked as {outcome}'}), 200

@deal_bp.route('/api/deals/forecast', methods=['GET'])
@token_required
def forecast_revenue(current_user):
    # Forecast logic: Sum of amount for Open deals in the organization
    total = db.session.query(
        func.sum(Deal.amount)
    ).filter(
        Deal.organization_id == current_user.organization_id,
        Deal.status == "Open"
    ).scalar() or 0.0

    return jsonify({"forecast_revenue": total}), 200