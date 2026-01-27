from flask import Blueprint, jsonify
from extensions import db
from models.crm import Deal
from routes.auth_routes import token_required
from sqlalchemy import func

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/api/analytics/win-loss', methods=['GET'])
@token_required
def win_loss_summary(current_user):
    # Filter by organization
    wins = Deal.query.filter_by(organization_id=current_user.organization_id, outcome="WON").count()
    losses = Deal.query.filter_by(organization_id=current_user.organization_id, outcome="LOST").count()
    
    return jsonify({
        "wins": wins,
        "losses": losses
    }), 200

@analytics_bp.route('/api/analytics/win-reasons', methods=['GET'])
@token_required
def win_reasons(current_user):
    rows = db.session.query(
        Deal.win_reason,
        func.count(Deal.id)
    ).filter(
        Deal.organization_id == current_user.organization_id,
        Deal.outcome == "WON"
    ).group_by(Deal.win_reason).all()

    return jsonify([{"reason": r[0], "count": r[1]} for r in rows]), 200

@analytics_bp.route('/api/analytics/loss-reasons', methods=['GET'])
@token_required
def loss_reasons(current_user):
    rows = db.session.query(
        Deal.loss_reason,
        func.count(Deal.id)
    ).filter(
        Deal.organization_id == current_user.organization_id,
        Deal.outcome == "LOST"
    ).group_by(Deal.loss_reason).all()

    return jsonify([{"reason": r[0], "count": r[1]} for r in rows]), 200