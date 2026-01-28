from flask import Blueprint, jsonify, g
from extensions import db
from models.activity_log import ActivityLog
from routes.auth_routes import token_required

activity_bp = Blueprint('activity', __name__)

@activity_bp.route('/activity-timeline', methods=['GET'])
@token_required
def get_activity_timeline(current_user):
    """
    Fetches a timeline of activities for the current user's company.
    """
    if not g.company_id:
        return jsonify({"error": "Company context not found"}), 400

    logs = ActivityLog.query.filter_by(
        company_id=g.company_id
    ).order_by(ActivityLog.created_at.desc()).limit(100).all()

    return jsonify([log.to_dict() for log in logs]), 200