from flask import Blueprint, request, jsonify
from extensions import db
from routes.auth_routes import token_required
from models.campaign import Campaign
from models.crm import Lead
from models.crm import Deal
from models.landing_page import LandingPageEvent
from sqlalchemy import func, extract
import calendar

marketing_analytics_bp = Blueprint('marketing_analytics', __name__)

@marketing_analytics_bp.route('/api/marketing/stats', methods=['GET'])
@token_required
def get_marketing_stats(current_user):
    branch_id = request.args.get('branchId')
    org_id = current_user.organization_id
    
    # Base Queries
    campaigns_query = Campaign.query.filter_by(organization_id=org_id)
    leads_query = Lead.query.filter_by(organization_id=org_id)
    
    # KPIs
    total_campaigns = campaigns_query.count()
    leads_generated = leads_query.count()
    
    # Total Revenue (Won Deals)
    total_revenue = db.session.query(func.sum(Deal.value)).filter_by(organization_id=org_id, stage='Won').scalar() or 0
    
    # Conversion Rate (Leads / Landing Page Views)
    total_views = LandingPageEvent.query.filter_by(organization_id=org_id, event_type='view').count()
    total_conversions = LandingPageEvent.query.filter_by(organization_id=org_id, event_type='conversion').count()
    conversion_rate = (total_conversions / total_views * 100) if total_views > 0 else 0
    
    # Channel Stats
    channel_stats = db.session.query(
        Campaign.channel, func.count(Campaign.id)
    ).filter_by(organization_id=org_id).group_by(Campaign.channel).all()
    
    channel_data = {c[0]: c[1] for c in channel_stats}
    
    # Funnel (Leads by Status)
    funnel_stats = db.session.query(
        Lead.status, func.count(Lead.id)
    ).filter_by(organization_id=org_id).group_by(Lead.status).all()
    
    funnel_data = {f[0]: f[1] for f in funnel_stats}
    
    # Trends (Leads by Month)
    trends_results = db.session.query(
        func.strftime('%m', Lead.created_at).label('month'),
        func.count(Lead.id)
    ).filter_by(organization_id=org_id).group_by('month').all()
    
    trends_data = []
    for r in trends_results:
        month_name = calendar.month_abbr[int(r[0])]
        trends_data.append({"month": month_name, "leads": r[1]})

    return jsonify({
        "total_campaigns": total_campaigns,
        "leads_generated": leads_generated,
        "conversion_rate": round(conversion_rate, 2),
        "total_revenue": total_revenue,
        "channel_stats": channel_data,
        "funnel": funnel_data,
        "trends": trends_data
    }), 200