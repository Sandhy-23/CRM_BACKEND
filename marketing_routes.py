from flask import Blueprint, jsonify

marketing_bp = Blueprint('marketing', __name__)

@marketing_bp.route('/analytics', methods=['GET'])
def get_marketing_analytics():
    # Placeholder data to fix 404
    return jsonify({
        "campaign_performance": [],
        "lead_sources": []
    }), 200