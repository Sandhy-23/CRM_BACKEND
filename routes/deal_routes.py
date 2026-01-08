from flask import Blueprint, request, jsonify
from extensions import db
from models.crm import Deal
from models.user import User
from models.activity_log import ActivityLog
from routes.auth_routes import token_required
from datetime import datetime

deal_bp = Blueprint('deals', __name__)

def get_deal_query(current_user):
    """Enforce Zoho-style Role Based Access Control for Deals"""
    query = Deal.query
    
    # Filter by Organization (using company_id as org_id based on schema)
    query = query.filter_by(company_id=current_user.organization_id)

    if current_user.role == 'Super Admin':
        return query

    if current_user.role == 'Admin':
        return query
    
    if current_user.role == 'Manager':
        team_ids = [u.id for u in User.query.filter_by(organization_id=current_user.organization_id, department=current_user.department).all()]
        return query.filter(Deal.owner_id.in_(team_ids))
    
    if current_user.role == 'Employee':
        return query.filter_by(owner_id=current_user.id)
    
    return query.filter_by(id=None)

@deal_bp.route('/api/deals', methods=['POST'])
@token_required
def create_deal(current_user):
    data = request.get_json()
    if not data:
        return jsonify({'message': 'Invalid JSON data'}), 400
    
    # Support 'deal_name' from legacy requests/Postman
    deal_name = data.get('deal_name') or data.get('title')
    if not deal_name or not data.get('stage'):
        print(f"❌ Validation Error (Create Deal): Missing deal_name or stage. Received: {data}")
        return jsonify({'error': 'Validation error', 'message': 'Deal name is required'}), 400

    new_deal = Deal(
        deal_name=deal_name,
        amount=data.get('amount', 0),
        stage=data.get('stage'),
        probability=data.get('probability', 0),
        owner_id=data.get('owner_id', current_user.id),
        created_at=datetime.utcnow()
    )
    # Assign Organization
    new_deal.company_id = current_user.organization_id
    
    db.session.add(new_deal)
    db.session.commit()
    
    return jsonify({'message': 'Deal created successfully', 'deal_id': new_deal.id}), 201

@deal_bp.route('/api/deals', methods=['GET'])
@token_required
def get_deals(current_user):
    query = get_deal_query(current_user)
    deals = query.order_by(Deal.created_at.desc()).all()
    
    result = [{
        "id": d.id,
        "deal_name": d.deal_name,
        "amount": d.amount,
        "stage": d.stage,
        "probability": d.probability,
        "owner_id": d.owner_id
    } for d in deals]
    
    return jsonify(result), 200

@deal_bp.route('/api/deals/<int:deal_id>', methods=['PUT'])
@token_required
def update_deal(current_user, deal_id):
    deal = get_deal_query(current_user).filter_by(id=deal_id).first()
    if not deal:
        return jsonify({'message': 'Deal not found'}), 404

    data = request.get_json()
    if 'stage' in data: deal.stage = data['stage']
    if 'amount' in data: deal.amount = data['amount']
    
    db.session.commit()
    return jsonify({'message': 'Deal updated successfully'}), 200