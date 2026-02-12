from flask import Blueprint, request, jsonify
from extensions import db
from models.crm import Deal
from routes.auth_routes import token_required
from datetime import datetime, date
from sqlalchemy import func
from models.activity_logger import log_activity
from services.automation_engine import run_workflow

deal_bp = Blueprint('deals', __name__)

def get_deal_query(current_user):
    """
    Returns the base query for deals.
    (Auth is handled by @token_required, RBAC is removed for now).
    """
    return Deal.query.filter((Deal.is_deleted == False) | (Deal.is_deleted.is_(None)))

ALLOWED_PIPELINES = ["Deals", "Sales", "Partnership", "Enterprise"]
ALLOWED_STAGES = ["Proposal", "Negotiation", "Won", "Lost"]

@deal_bp.route('/api/deals', methods=['POST'])
@token_required
def create_deal(current_user):
    data = request.get_json()
    print("[DEBUG] /api/deals Body:", data)

    title = data.get("title") or data.get("name")
    
    # Auto-capitalize to handle frontend sending lowercase
    pipeline = data.get("pipeline", "").capitalize() if data.get("pipeline") else None
    stage = data.get("stage", "").capitalize() if data.get("stage") else None
    
    # Special case for "Partnership" if frontend sends "Partnerships"
    if pipeline == "Partnerships": pipeline = "Partnership"

    print("PIPELINE RECEIVED:", pipeline)
    print("STAGE RECEIVED:", stage)

    if not title:
        return jsonify({"error": "A 'title' or 'name' field is required"}), 400
    if not pipeline:
        return jsonify({"error": "The 'pipeline' field is required and cannot be empty"}), 400
    if not stage:
        return jsonify({"error": "The 'stage' field is required"}), 400

    if pipeline not in ALLOWED_PIPELINES:
        return jsonify({"error": "Invalid pipeline. Allowed: Deals, Sales, Partnership, Enterprise"}), 400

    if stage not in ALLOWED_STAGES:
        return jsonify({"error": "Invalid stage. Allowed: Proposal, Negotiation, Won, Lost"}), 400

    close_date_obj = None
    if data.get("close_date"):
        try:
            close_date_obj = datetime.strptime(data.get("close_date"), '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return jsonify({'message': 'Invalid close_date format. Use YYYY-MM-DD.'}), 400

    new_deal = Deal(
        lead_id=data.get('lead_id'), # Optional
        pipeline=pipeline,
        title=title,
        company=data.get("company"),
        stage=stage,
        value=data.get("value", 0),
        owner=data.get("owner"),
        close_date=close_date_obj,
        created_at=datetime.utcnow(),
        organization_id=current_user.organization_id
    )
    
    db.session.add(new_deal)
    db.session.commit()

    log_activity("deal", "created", f"Deal '{new_deal.title}' created in {new_deal.pipeline}.", new_deal.id)
    
    # AUTOMATION HOOK
    run_workflow("deal_created", new_deal)
    
    return jsonify({
        "message": "Deal created successfully",
        "deal_id": new_deal.id
    }), 201

@deal_bp.route('/api/deals', methods=['GET'])
@token_required
def get_deals(current_user):
    pipeline_filter = request.args.get('pipeline')
    query = get_deal_query(current_user)
    
    if pipeline_filter:
        query = query.filter_by(pipeline=pipeline_filter)
        
    deals = query.order_by(Deal.id.desc()).all()
    
    return jsonify({
        "deals": [{
            "id": d.id,
            "title": d.title,
            "company": d.company,
            "pipeline": d.pipeline,
            "stage": d.stage,
            "value": d.value,
            "owner": d.owner,
            "close_date": str(d.close_date) if d.close_date else None
        } for d in deals]
    }), 200

@deal_bp.route('/api/deals/pipelines', methods=['GET'])
@token_required
def get_all_pipelines(current_user):
    """Returns deals grouped by pipeline for the dashboard."""
    deals = get_deal_query(current_user).all()
    
    grouped = {}
    for d in deals:
        p_name = d.pipeline
        if p_name not in grouped:
            grouped[p_name] = []
        
        grouped[p_name].append({
            "id": d.id,
            "lead_id": d.lead_id,
            "title": d.title,
            "company": d.company,
            "stage": d.stage,
            "value": d.value,
            "owner": d.owner,
            "close": str(d.close_date) if d.close_date else None
        })
        
    return jsonify(grouped), 200

@deal_bp.route('/api/deals/<int:deal_id>', methods=['GET'])
@token_required
def get_deal(current_user, deal_id):
    d = get_deal_query(current_user).filter_by(id=deal_id).first_or_404()
    return jsonify({
        "id": d.id,
        "lead_id": d.lead_id,
        "title": d.title,
        "company": d.company,
        "pipeline": d.pipeline,
        "stage": d.stage,
        "value": d.value,
        "owner": d.owner,
        "close_date": str(d.close_date) if d.close_date else None
    })

@deal_bp.route('/api/deals/<int:deal_id>', methods=['PUT'])
@token_required
def update_deal(current_user, deal_id):
    deal = get_deal_query(current_user).filter_by(id=deal_id).first()
    if not deal:
        return jsonify({'message': 'Deal not found'}), 404

    old_stage = deal.stage
    data = request.get_json()
    updated = False
    for field in ["title", "company", "stage", "value", "owner", "pipeline", "close_date"]:
        if field in data:
            if field == 'close_date':
                try:
                    close_date_obj = datetime.strptime(data.get("close_date"), '%Y-%m-%d').date() if data.get("close_date") else None
                    setattr(deal, field, close_date_obj)
                except (ValueError, TypeError):
                    return jsonify({'message': 'Invalid close_date format. Use YYYY-MM-DD.'}), 400
            else:
                setattr(deal, field, data[field])
            updated = True
    
    if updated:
        db.session.commit()
        log_activity("deal", "updated", f"Deal '{deal.title}' was updated.", deal.id)
        
        # AUTOMATION HOOK
        if old_stage != deal.stage:
            run_workflow("deal_updated", deal)
            
        return jsonify({'message': 'Deal updated successfully'}), 200
    
    return jsonify({'message': 'No valid fields provided for update'}), 400

@deal_bp.route('/api/deals/<int:deal_id>', methods=['DELETE'])
@token_required
def delete_deal(current_user, deal_id):
    deal = get_deal_query(current_user).filter_by(id=deal_id).first()
    if not deal:
        return jsonify({'message': f'Deal with ID {deal_id} not found.'}), 404

    deal.is_deleted = True
    deal.deleted_at = datetime.utcnow()
    
    db.session.commit()
    log_activity("deal", "deleted", f"Deal '{deal.title}' was deleted.", deal.id)
    return jsonify({'message': 'Deal deleted successfully'}), 200

@deal_bp.route('/api/deals/<int:deal_id>/status', methods=['PUT'])
@token_required
def update_deal_status(current_user, deal_id):
    deal = get_deal_query(current_user).filter_by(id=deal_id, organization_id=current_user.organization_id).first()
    if not deal:
        return jsonify({'message': 'Deal not found'}), 404

    old_stage = deal.stage
    data = request.get_json()
    new_status = data.get('status')

    if new_status not in ['won', 'lost']:
         return jsonify({'message': 'Invalid status. Must be "won" or "lost"'}), 400

    # The model uses 'stage', so we map 'status' to 'stage'
    new_stage = new_status.capitalize()

    if new_stage == 'Won':
        deal.stage = 'Won'
        deal.win_reason = data.get('win_reason')
        deal.closed_at = datetime.utcnow()
    elif new_stage == 'Lost':
        deal.stage = 'Lost'
        deal.loss_reason = data.get('loss_reason')
        deal.closed_at = datetime.utcnow()
    
    db.session.commit()
    log_activity("deal", "status_changed", f"Deal '{deal.title}' status changed to {new_stage}.", deal.id)
    
    # AUTOMATION HOOK
    if old_stage != deal.stage:
        run_workflow("deal_updated", deal)

    return jsonify({'message': f'Deal status updated to {new_stage}'}), 200

@deal_bp.route('/api/deals/analytics', methods=['GET'])
@token_required
def get_deal_analytics(current_user):
    # 1. Win / Loss / In-progress count
    won = Deal.query.filter_by(stage="Won").count()
    lost = Deal.query.filter_by(stage="Lost").count()
    in_progress = Deal.query.filter(Deal.stage.notin_(["Won", "Lost"])).count()
    
    # Total Value
    total_value = db.session.query(func.sum(Deal.value)).filter(Deal.stage.notin_(['Won', 'Lost'])).scalar() or 0
    open_deals = in_progress

    # Static reasons for demo phase as requested
    win_reasons = [
        { "label": "Pricing Fit", "value": 35 },
        { "label": "Product Match", "value": 25 }
    ]
    loss_reasons = [
        { "label": "Budget Issues", "value": 30 },
        { "label": "Competitor Chosen", "value": 22 }
    ]
    
    return jsonify({
        "summary": {
            "total_value": int(total_value),
            "open_deals": open_deals,
            "won": won,
            "lost": lost
        },
        "win_loss": {
            "won": won,
            "lost": lost,
            "in_progress": in_progress
        },
        "win_reasons": win_reasons,
        "loss_reasons": loss_reasons
    })