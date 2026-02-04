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
    wins = Deal.query.filter(Deal.stage == 'Won').count()
    losses = Deal.query.filter(Deal.stage == 'Lost').count()
    
    return jsonify({
        "wins": wins,
        "losses": losses
    }), 200

@analytics_bp.route('/api/analytics/win-reasons', methods=['GET'])
@token_required
def win_reasons(current_user):
    results = db.session.query(Deal.win_reason, func.count(Deal.id))\
        .filter(Deal.stage == 'Won', Deal.win_reason.isnot(None), Deal.win_reason != "")\
        .group_by(Deal.win_reason).all()
    
    return jsonify([{"label": r[0], "value": r[1]} for r in results]), 200

@analytics_bp.route('/api/analytics/loss-reasons', methods=['GET'])
@token_required
def loss_reasons(current_user):
    results = db.session.query(Deal.loss_reason, func.count(Deal.id))\
        .filter(Deal.stage == 'Lost', Deal.loss_reason.isnot(None), Deal.loss_reason != "")\
        .group_by(Deal.loss_reason).all()
    
    return jsonify([{"label": r[0], "value": r[1]} for r in results]), 200