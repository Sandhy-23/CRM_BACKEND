from flask import Blueprint, jsonify
from extensions import db
from models.crm import Lead, Deal
from routes.auth_routes import token_required
from sqlalchemy import func, extract
from datetime import datetime, timedelta
import calendar

report_bp = Blueprint('reports', __name__)

# 1️⃣ Reports Summary API (Top cards)
@report_bp.route('/api/reports/summary', methods=['GET'])
@token_required
def get_reports_summary(current_user):
    # Total Leads
    total_leads = Lead.query.count()
    
    # Active Deals (Assuming 'Proposal' and 'Negotiation' are active stages based on previous context, 
    # or strictly 'active' if status column was migrated. Using stage logic for consistency with Deal model)
    # The prompt asks for status='active', but Deal model uses 'stage'. 
    # Mapping: Active = Not Won/Lost.
    active_deals = Deal.query.filter(Deal.stage.notin_(['Won', 'Lost'])).count()
    
    # Revenue (Sum of value of Won deals)
    revenue = db.session.query(func.sum(Deal.value)).filter(Deal.stage == 'Won').scalar() or 0
    
    # Conversion Rate (Converted Leads / Total Leads * 100)
    # Assuming 'Converted' status exists for Leads
    converted_leads = Lead.query.filter_by(status='Converted').count()
    conversion_rate = round((converted_leads / total_leads * 100), 2) if total_leads > 0 else 0

    return jsonify({
        "total_leads": total_leads,
        "conversion_rate": conversion_rate,
        "revenue": int(revenue),
        "active_deals": active_deals
    }), 200

# 2️⃣ Leads Trend API (Line chart)
@report_bp.route('/api/reports/leads-trend', methods=['GET'])
@token_required
def get_leads_trend(current_user):
    # Last 6 months data
    today = datetime.utcnow().date()
    six_months_ago = today - timedelta(days=180)
    
    # Group by Month
    # SQLite extract syntax: strftime('%m', created_at)
    # SQLAlchemy extract('month', ...) works for most DBs
    
    results = db.session.query(
        func.strftime('%Y-%m', Lead.created_at).label('month_year'),
        func.count(Lead.id)
    ).filter(
        Lead.created_at >= six_months_ago
    ).group_by(
        'month_year'
    ).order_by(
        'month_year'
    ).all()
    
    # Format response: "Aug", "Sep", etc.
    trend_data = []
    for r in results:
        date_obj = datetime.strptime(r[0], '%Y-%m')
        month_name = date_obj.strftime('%b')
        trend_data.append({
            "month": month_name,
            "leads": r[1]
        })
        
    return jsonify(trend_data), 200

# 3️⃣ Lead Sources API
@report_bp.route('/api/reports/lead-sources', methods=['GET'])
@token_required
def get_lead_sources(current_user):
    results = db.session.query(
        Lead.source,
        func.count(Lead.id)
    ).group_by(
        Lead.source
    ).all()
    
    sources_data = [{"source": r[0], "leads": r[1]} for r in results]
    return jsonify(sources_data), 200

# 4️⃣ Insights API
@report_bp.route('/api/reports/insights', methods=['GET'])
@token_required
def get_insights(current_user):
    insights = []
    
    # Insight 1: Top Source
    top_source = db.session.query(Lead.source, func.count(Lead.id))\
        .group_by(Lead.source).order_by(func.count(Lead.id).desc()).first()
        
    total_leads = Lead.query.count()
    
    if top_source and total_leads > 0:
        percentage = round((top_source[1] / total_leads * 100))
        insights.append(f"{top_source[0]} generate the highest quality leads with {percentage}% contribution.")
    
    # Insight 2: Conversion Rate Comparison (Current Month vs Last Month)
    today = datetime.utcnow()
    first_day_this_month = today.replace(day=1)
    last_month_end = first_day_this_month - timedelta(days=1)
    first_day_last_month = last_month_end.replace(day=1)
    
    # This Month
    leads_this_month = Lead.query.filter(Lead.created_at >= first_day_this_month).count()
    conv_this_month = Lead.query.filter(Lead.created_at >= first_day_this_month, Lead.status == 'Converted').count()
    rate_this_month = (conv_this_month / leads_this_month * 100) if leads_this_month > 0 else 0
    
    # Last Month
    leads_last_month = Lead.query.filter(Lead.created_at >= first_day_last_month, Lead.created_at <= last_month_end).count()
    conv_last_month = Lead.query.filter(Lead.created_at >= first_day_last_month, Lead.created_at <= last_month_end, Lead.status == 'Converted').count()
    rate_last_month = (conv_last_month / leads_last_month * 100) if leads_last_month > 0 else 0
    
    diff = rate_this_month - rate_last_month
    if diff > 0:
        insights.append(f"Conversion rate improved by {round(diff)}% compared to last month.")
    elif diff < 0:
        insights.append(f"Conversion rate dropped by {abs(round(diff))}% compared to last month.")
    else:
        insights.append("Conversion rate remained stable compared to last month.")

    # Insight 3: Recent Performance (Last 2 weeks vs Previous 2 weeks) - Simplified placeholder logic
    # Real logic would require tracking daily performance per source which is complex.
    # Providing a static or simple dynamic insight for now.
    
    # Check if total leads dropped recently
    two_weeks_ago = today - timedelta(days=14)
    recent_leads = Lead.query.filter(Lead.created_at >= two_weeks_ago).count()
    if recent_leads < (total_leads / 12): # Rough heuristic
        insights.append("Lead generation slowed down slightly in the last 2 weeks.")
    else:
        insights.append("Lead generation is steady in the last 2 weeks.")

    return jsonify(insights), 200

# 5️⃣ Top Win Reasons API
@report_bp.route('/api/reports/deals/top-win-reasons', methods=['GET'])
@token_required
def get_top_win_reasons(current_user):
    # Get total won deals for the organization
    total_won = Deal.query.filter_by(stage='Won', organization_id=current_user.organization_id).count()

    if total_won == 0:
        return jsonify([])

    # Get counts for each win reason
    results = db.session.query(Deal.win_reason, func.count(Deal.id))\
        .filter(Deal.stage == 'Won', Deal.organization_id == current_user.organization_id, Deal.win_reason.isnot(None))\
        .group_by(Deal.win_reason).all()

    response_data = []
    for reason, count in results:
        if reason: # Ensure reason is not empty
            percentage = (count / total_won) * 100
            response_data.append({"reason": reason, "percentage": round(percentage)})
            
    return jsonify(sorted(response_data, key=lambda x: x['percentage'], reverse=True))

# 6️⃣ Top Loss Reasons API
@report_bp.route('/api/reports/deals/top-loss-reasons', methods=['GET'])
@token_required
def get_top_loss_reasons(current_user):
    # Get total lost deals for the organization
    total_lost = Deal.query.filter_by(stage='Lost', organization_id=current_user.organization_id).count()

    if total_lost == 0:
        return jsonify([])

    results = db.session.query(Deal.loss_reason, func.count(Deal.id))\
        .filter(Deal.stage == 'Lost', Deal.organization_id == current_user.organization_id, Deal.loss_reason.isnot(None))\
        .group_by(Deal.loss_reason).all()

    response_data = []
    for reason, count in results:
        if reason:
            percentage = (count / total_lost) * 100
            response_data.append({"reason": reason, "percentage": round(percentage)})
            
    return jsonify(sorted(response_data, key=lambda x: x['percentage'], reverse=True))