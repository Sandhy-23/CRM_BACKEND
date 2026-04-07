from flask import Blueprint, request, jsonify
from extensions import db
from models.crm import Deal, Lead
from db import get_engine
from sqlalchemy import text
from routes.auth_routes import token_required, permission_required
from datetime import datetime, date
from sqlalchemy import func
from models.activity_logger import log_activity
# from services.automation_engine import run_workflow

deal_bp = Blueprint('deals', __name__)

ALLOWED_STAGES = ["Proposal", "Negotiation", "Won", "Lost"]

def get_pipeline(value, lead_source):
    """
    🔥 STEP 2: Logic Priority
    1. Partnership (Source based)
    2. Enterprise (Value >= 1M)
    3. Sales (Default)
    """
    if lead_source in ['Partner', 'Referral']:
        return 'Partnership'
    elif (value or 0) >= 1000000:
        return 'Enterprise'
    return 'Sales'

@deal_bp.route('/api/deals', methods=['POST'])
@token_required
@permission_required("Deals", "create")
def create_deal(current_user):
    data = request.get_json()
    print("[DEBUG] /api/deals Body:", data)

    title = data.get("title") or data.get("name")
    
    stage = data.get("stage", "").capitalize() if data.get("stage") else None

    if not title:
        return jsonify({"error": "A 'title' or 'name' field is required"}), 400
    if not stage:
        return jsonify({"error": "The 'stage' field is required"}), 400

    if stage not in ALLOWED_STAGES:
        return jsonify({"error": "Invalid stage. Allowed: Proposal, Negotiation, Won, Lost"}), 400

    close_date_obj = None
    if data.get("close_date"):
        try:
            close_date_obj = datetime.strptime(data.get("close_date"), '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return jsonify({'message': 'Invalid close_date format. Use YYYY-MM-DD.'}), 400

    # Dynamically determine pipeline
    value = data.get("value", 0)
    lead_id = data.get('lead_id')
    
    lead_source = None
    if lead_id:
        lead = db.session.get(Lead, lead_id)
        lead_source = lead.source if lead else None
    
    pipeline = get_pipeline(value, lead_source)

    engine = get_engine(current_user.tenant_db)
    with engine.begin() as conn:
        result = conn.execute(text("""
            INSERT INTO deals (lead_id, pipeline, lead_source, title, company, stage, value, owner, close_date, created_at, organization_id)
            VALUES (:lead_id, :pipeline, :lead_source, :title, :company, :stage, :value, :owner, :close_date, :created_at, :org_id)
        """), {
            "lead_id": lead_id, "pipeline": pipeline, "lead_source": lead_source, "title": title,
            "company": data.get("company"), "stage": stage, "value": value, "owner": data.get("owner"),
            "close_date": close_date_obj, "created_at": datetime.utcnow(), "org_id": current_user.organization_id
        })
        new_deal_id = result.lastrowid

    log_activity("deal", "created", f"Deal '{title}' created in {pipeline}.", new_deal_id)
    
    # AUTOMATION HOOK
    # run_workflow("deal_created", new_deal)
    
    return jsonify({
        "message": "Deal created successfully",
        "deal_id": new_deal_id
    }), 201

@deal_bp.route('/api/deals', methods=['GET'])
@token_required
@permission_required("Deals", "view")
def get_deals(current_user):
    pipeline_filter = request.args.get('pipeline')
    if pipeline_filter:
        pipeline_filter = pipeline_filter.lower()
    
    engine = get_engine(current_user.tenant_db)
    with engine.connect() as conn:
        sql = "SELECT * FROM deals WHERE organization_id = :org_id AND is_deleted = 0"
        if pipeline_filter:
            sql += " AND LOWER(pipeline) = :pipeline"
        
        result = conn.execute(text(sql), {"org_id": current_user.organization_id, "pipeline": pipeline_filter}).fetchall()
        deals = [dict(row._mapping) for row in result]
    final_deals = []
    for deal in deals:
        d_dict = {
            "id": deal['id'],
            "deal_name": deal['title'],
            "company": deal['company'],
            "pipeline": deal['pipeline'],
            "stage": deal['stage'],
            "value": deal['value'],
            "owner": deal['owner'],
            "close_date": str(deal['close_date']) if deal['close_date'] else None
        }
        final_deals.append(d_dict)

    return jsonify({"deals": final_deals}), 200

@deal_bp.route('/api/deals/pipelines', methods=['GET'])
@token_required
def get_all_pipelines(current_user):
    """Returns deals grouped by pipeline for the dashboard."""
    engine = get_engine(current_user.tenant_db)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM deals WHERE organization_id = :org_id AND is_deleted = 0"), 
                              {"org_id": current_user.organization_id}).fetchall()
        deals = [dict(row._mapping) for row in result]
    
    grouped = {}
    for deal in deals:
        # Use dictionary access for raw SQL mapping
        p_name = deal['pipeline'] or "Default"
        
        if p_name not in grouped:
            grouped[p_name] = []
        
        grouped[p_name].append({
            "id": deal['id'],
            "lead_id": deal['lead_id'],
            "title": deal['title'],
            "company": deal['company'],
            "stage": deal['stage'],
            "value": deal['value'],
            "owner": deal['owner'],
            "close": str(deal['close_date']) if deal['close_date'] else None
        })
        
    return jsonify(grouped), 200

@deal_bp.route('/api/deals/<int:deal_id>', methods=['GET'])
@token_required
def get_deal(current_user, deal_id):
    engine = get_engine(current_user.tenant_db)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM deals WHERE id = :id AND organization_id = :org_id AND is_deleted = 0"), 
                              {"id": deal_id, "org_id": current_user.organization_id}).fetchone()
        if not result:
            return jsonify({"error": "Deal not found"}), 404
        deal = dict(result._mapping)

    return jsonify({
        "id": deal['id'],
        "lead_id": deal['lead_id'],
        "title": deal['title'],
        "company": deal['company'],
        # Use the stored pipeline name directly
        "pipeline": deal['pipeline'], 
        "stage": deal['stage'],
        "value": deal['value'],
        "owner": deal['owner'],
        "close_date": str(deal['close_date']) if deal['close_date'] else None
    })

@deal_bp.route('/api/deals/<int:deal_id>', methods=['PUT'])
@token_required
def update_deal(current_user, deal_id):
    data = request.get_json()
    engine = get_engine(current_user.tenant_db)
    
    with engine.begin() as conn:
        # 1. Fetch current record
        deal = conn.execute(text("SELECT * FROM deals WHERE id = :id AND organization_id = :org_id"), 
                            {"id": deal_id, "org_id": current_user.organization_id}).fetchone()
        if not deal:
            return jsonify({'message': 'Deal not found'}), 404
        
        deal = dict(deal._mapping)
        
        # 2. Update logic
        val = data.get("value", deal['value'])
        l_id = data.get("lead_id", deal['lead_id'])
        
        # Recalculate pipeline if source data changes
        l_source = deal['lead_source']
        if "lead_id" in data:
            l_res = conn.execute(text("SELECT source FROM leads WHERE id = :id"), {"id": l_id}).fetchone()
            l_source = l_res[0] if l_res else None

        new_pipeline = get_pipeline(val, l_source)

        conn.execute(text("""
            UPDATE deals SET 
                title = :title, company = :company, stage = :stage, value = :value, 
                owner = :owner, close_date = :close_date, lead_id = :lead_id, 
                lead_source = :l_source, pipeline = :pipeline
            WHERE id = :id
        """), {
            "title": data.get("title", deal['title']), "company": data.get("company", deal['company']),
            "stage": data.get("stage", deal['stage']), "value": val,
            "owner": data.get("owner", deal['owner']), "close_date": data.get("close_date", deal['close_date']),
            "lead_id": l_id, "l_source": l_source, "pipeline": new_pipeline, "id": deal_id
        })

    log_activity("deal", "updated", f"Deal '{deal['title']}' was updated.", deal_id)
    return jsonify({'message': 'Deal updated successfully'}), 200

# ✅ FIX 2: DELETE API
@deal_bp.route('/api/deals/<int:deal_id>', methods=['DELETE'])
@token_required
@permission_required("Deals", "delete")
def delete_deal(current_user, deal_id):
    engine = get_engine(current_user.tenant_db)
    with engine.begin() as conn:
        result = conn.execute(text("DELETE FROM deals WHERE id = :id AND organization_id = :org_id"), 
                              {"id": deal_id, "org_id": current_user.organization_id})
        if result.rowcount == 0:
            return jsonify({"error": "Deal not found"}), 404

    return jsonify({"message": "Deleted successfully"}), 200

@deal_bp.route('/api/deals/<int:deal_id>/status', methods=['PUT'])
@token_required
def update_deal_status(current_user, deal_id):
    data = request.get_json()
    status = data.get('status', '').lower()
    if status not in ['won', 'lost']:
        return jsonify({'message': 'Invalid status'}), 400

    engine = get_engine(current_user.tenant_db)
    with engine.begin() as conn:
        result = conn.execute(text("""
            UPDATE deals SET stage = :stage, win_reason = :win, loss_reason = :loss, closed_at = :now
            WHERE id = :id AND organization_id = :org_id
        """), {
            "stage": status.capitalize(), "win": data.get('win_reason'), "loss": data.get('loss_reason'),
            "now": datetime.utcnow(), "id": deal_id, "org_id": current_user.organization_id
        })
        if result.rowcount == 0:
            return jsonify({'message': 'Deal not found'}), 404

    log_activity("deal", "status_changed", f"Deal ID {deal_id} status changed to {status}.", deal_id)
    return jsonify({'message': f'Deal status updated to {status}'}), 200

@deal_bp.route('/api/deals/analytics', methods=['GET', 'OPTIONS'])
@token_required
def get_deal_analytics(current_user):
    engine = get_engine(current_user.tenant_db)
    with engine.connect() as conn:
        # 1. Counts
        won = conn.execute(text("SELECT COUNT(*) FROM deals WHERE stage = 'Won' AND organization_id = :org_id"), {"org_id": current_user.organization_id}).scalar()
        lost = conn.execute(text("SELECT COUNT(*) FROM deals WHERE stage = 'Lost' AND organization_id = :org_id"), {"org_id": current_user.organization_id}).scalar()
        in_progress = conn.execute(text("SELECT COUNT(*) FROM deals WHERE stage NOT IN ('Won', 'Lost') AND organization_id = :org_id"), {"org_id": current_user.organization_id}).scalar()

        # ✅ Step 2 & 3: Define required analytics variables
        open_deals = conn.execute(text("SELECT COUNT(*) FROM deals WHERE status = 'open' AND organization_id = :org_id"), {"org_id": current_user.organization_id}).scalar() or 0
        won_deals = conn.execute(text("SELECT COUNT(*) FROM deals WHERE status = 'won' AND organization_id = :org_id"), {"org_id": current_user.organization_id}).scalar() or 0
        lost_deals = conn.execute(text("SELECT COUNT(*) FROM deals WHERE status = 'lost' AND organization_id = :org_id"), {"org_id": current_user.organization_id}).scalar() or 0
        
        # 2. Total Value
        total_value = conn.execute(text("SELECT SUM(value) FROM deals WHERE stage NOT IN ('Won', 'Lost') AND organization_id = :org_id"), {"org_id": current_user.organization_id}).scalar() or 0

    # Static reasons for demo phase as requested
    win_reasons = [
        { "label": "Pricing Fit", "value": 35 },
        { "label": "Product Match", "value": 25 }
    ]
    loss_reasons = [
        { "label": "Budget Issues", "value": 30 },
        { "label": "Competitor Chosen", "value": 22 }
    ]
    
    # ✅ Step 4: Return properly
    return jsonify({
        "open_deals": open_deals,
        "won_deals": won_deals,
        "lost_deals": lost_deals
    })