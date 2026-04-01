from flask import Blueprint, jsonify
from extensions import db
from models.campaign import Campaign
from routes.auth_routes import token_required

marketing_analytics_bp = Blueprint('marketing_analytics', __name__)

@marketing_analytics_bp.route('/api/marketing/analytics', methods=['GET'])
@token_required
def get_marketing_analytics(current_user):
    
    # Fetch campaigns for the current user's organization
    campaigns = Campaign.query.filter_by(organization_id=current_user.organization_id).all()

    campaign_list = []
    for c in campaigns:
        # Using getattr to avoid crashes if columns don't exist in current DB schema
        leads = getattr(c, 'leads', 0) or 0
        revenue = getattr(c, 'revenue', 0) or 0
        conversion = getattr(c, 'conversion', 0) or 0
        date_val = getattr(c, 'date', c.created_at)

        campaign_list.append({
            "name": c.name,
            "channel": c.channel,
            "status": c.status,
            "leads": leads,
            "conversion": f"{conversion}%",
            "revenue": f"₹{revenue}",
            "date": str(date_val)
        })

    total_campaigns = len(campaigns)
    total_leads = sum((getattr(c, 'leads', 0) or 0) for c in campaigns)
    total_revenue = sum((getattr(c, 'revenue', 0) or 0) for c in campaigns)

    response = {
        "kpis": {
            "totalCampaigns": {"value": total_campaigns, "growth": "+0%"},
            "leadsGenerated": {"value": total_leads, "growth": "+0%"},
            "conversionRate": {"value": 0, "growth": "+0%"},
            "totalRevenue": {"value": total_revenue, "growth": "+0%"}
        },
        "channels": [],   # keep empty as requested
        "campaigns": campaign_list
    }

    print("FINAL RESPONSE:", response)

    return jsonify(response)