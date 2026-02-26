from flask import Blueprint, jsonify, request
from extensions import db
from models.campaign import Campaign
from models.crm import Lead, Deal
from routes.auth_routes import token_required
from sqlalchemy import func, case
from datetime import datetime
import calendar

marketing_analytics_bp = Blueprint('marketing_analytics', __name__)

@marketing_analytics_bp.route('/api/marketing/analytics', methods=['GET'])
@token_required
def get_marketing_analytics(current_user):
    org_id = current_user.organization_id

    # 1️⃣ Summary Metrics
    total_campaigns = Campaign.query.filter_by(organization_id=org_id).count()
    total_leads = Lead.query.filter_by(organization_id=org_id, is_deleted=False).count()
    
    # Revenue from Won Deals
    revenue = db.session.query(func.sum(Deal.value)).filter(
        Deal.organization_id == org_id,
        Deal.stage.ilike('%won%'),
        Deal.is_deleted == False
    ).scalar() or 0

    # Conversion Rate
    won_deals_count = Deal.query.filter(
        Deal.organization_id == org_id,
        Deal.stage.ilike('%won%'),
        Deal.is_deleted == False
    ).count()
    
    conversion_rate = 0
    if total_leads > 0:
        conversion_rate = round((won_deals_count / total_leads) * 100, 2)

    # 2️⃣ Monthly Trend (Leads)
    # SQLite uses strftime, MySQL uses DATE_FORMAT. Assuming SQLite based on context.
    monthly_trends = db.session.query(
        func.strftime('%Y-%m', Lead.created_at).label('month'),
        func.count(Lead.id)
    ).filter(
        Lead.organization_id == org_id,
        Lead.is_deleted == False
    ).group_by('month').order_by('month').all()

    trend_data = []
    for mt in monthly_trends:
        if mt[0]:
            year, month = mt[0].split('-')
            month_name = calendar.month_abbr[int(month)]
            trend_data.append({"name": f"{month_name}", "leads": mt[1]})

    # 3️⃣ Funnel Analysis
    # Leads -> Opportunities (Deals Created) -> Wins
    total_opportunities = Deal.query.filter_by(organization_id=org_id, is_deleted=False).count()
    
    funnel_data = [
        {"name": "Total Leads", "value": total_leads, "fill": "#8884d8"},
        {"name": "Opportunities", "value": total_opportunities, "fill": "#82ca9d"},
        {"name": "Wins", "value": won_deals_count, "fill": "#ffc658"}
    ]

    # 4️⃣ Channel Performance (Lead Source)
    channel_stats = db.session.query(
        Lead.source,
        func.count(Lead.id)
    ).filter(
        Lead.organization_id == org_id,
        Lead.is_deleted == False
    ).group_by(Lead.source).all()

    channel_data = [{"name": cs[0] or "Unknown", "value": cs[1]} for cs in channel_stats]

    # 5️⃣ Campaign Performance
    # Join Campaign -> Lead -> Deal to get ROI per campaign
    campaigns = Campaign.query.filter_by(organization_id=org_id).all()
    campaign_performance = []

    for camp in campaigns:
        # Count Leads for this campaign
        camp_leads = Lead.query.filter_by(campaign_id=str(camp.id), is_deleted=False).count()
        
        # Calculate Revenue (Deals from Leads of this campaign)
        # Note: This requires Leads to have campaign_id populated
        camp_revenue = db.session.query(func.sum(Deal.value)).join(Lead, Deal.lead_id == Lead.id).filter(
            Lead.campaign_id == str(camp.id),
            Deal.stage.ilike('%won%'),
            Deal.is_deleted == False
        ).scalar() or 0

        # ROI Calculation
        roi = 0
        if camp.spent and camp.spent > 0:
            roi = round(((camp_revenue - camp.spent) / camp.spent) * 100, 2)

        campaign_performance.append({
            "id": camp.id,
            "name": camp.name,
            "status": camp.status,
            "leads": camp_leads,
            "revenue": camp_revenue,
            "spent": camp.spent or 0,
            "roi": roi
        })

    return jsonify({
        "kpis": {
            "total_campaigns": total_campaigns,
            "total_leads": total_leads,
            "conversion_rate": conversion_rate,
            "revenue": revenue
        },
        "trend_data": trend_data,
        "funnel_data": funnel_data,
        "channel_data": channel_data,
        "campaign_performance": campaign_performance
    }), 200