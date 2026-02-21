from flask import Blueprint, jsonify, request
from extensions import db
from models.crm import Lead, Deal
from models.user import User
from sqlalchemy import func, desc, text
from datetime import datetime, timedelta

reports_bp = Blueprint('reports_new', __name__) # Register as /api/reports in app.py

def get_date_filter():
    """Helper to parse start and end date from query params."""
    start_str = request.args.get('start')
    end_str = request.args.get('end')
    
    if start_str and end_str:
        try:
            start_date = datetime.strptime(start_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_str, '%Y-%m-%d') + timedelta(days=1) # Include end date
            return start_date, end_date
        except ValueError:
            pass
    
    # Default to current month
    today = datetime.utcnow()
    start_date = today.replace(day=1, hour=0, minute=0, second=0)
    # End date is now (up to current moment)
    return start_date, today

@reports_bp.route('/summary', methods=['GET'])
def get_summary():
    start_date, end_date = get_date_filter()
    
    # 1. Revenue (Sum of Won deals)
    revenue = db.session.query(func.sum(Deal.value)).filter(
        text("status = 'won'"), # Use status column as per prompt
        Deal.created_at >= start_date,
        Deal.created_at <= end_date
    ).scalar() or 0

    # 2. Total Leads
    leads_count = Lead.query.filter(
        Lead.created_at >= start_date,
        Lead.created_at <= end_date
    ).count() or 0

    # 3. Active Deals (Not Won or Lost)
    active_deals = Deal.query.filter(
        text("status = 'open'"),
        Deal.created_at >= start_date,
        Deal.created_at <= end_date
    ).count() or 0

    # 4. Conversion Rate
    won_deals_count = Deal.query.filter(
        text("status = 'won'"),
        Deal.created_at >= start_date,
        Deal.created_at <= end_date
    ).count()
    conversion = round((won_deals_count / leads_count * 100), 2) if leads_count > 0 else 0

    # 5. Best Performer (By Revenue)
    best_rep = db.session.query(Deal.owner, func.sum(Deal.value).label('total'))\
        .filter(text("status = 'won'"))\
        .group_by(Deal.owner)\
        .order_by(desc('total')).first()
    performer = best_rep[0] if best_rep else "N/A"

    # 6. Best Source
    best_source_q = db.session.query(Lead.source, func.count(Lead.id).label('cnt'))\
        .group_by(Lead.source)\
        .order_by(desc('cnt')).first()
    best_source = best_source_q[0] if best_source_q else "N/A"

    return jsonify({
        "summary": {
            "revenue": int(revenue),
            "leads": leads_count,
            "conversion": conversion,
            "performer": performer,
            "growth": 12.4, # Mocked for now as per prompt example
            "best_source": best_source,
            "active_deals": active_deals
        },
        "insights": [
            { "text": f"{best_source} is the best performing source." },
            { "text": f"{performer} is top performer this period." }
        ]
    })

@reports_bp.route('/leads', methods=['GET'])
def get_leads_report():
    # Group by Source and Location (City)
    results = db.session.query(
        Lead.source,
        Lead.city,
        func.count(Lead.id)
    ).group_by(Lead.source, Lead.city).all()

    report = []
    for r in results:
        report.append({
            "source": r[0] or "Unknown",
            "location": r[1] or "Unknown",
            "leads": r[2],
            "growth": 10 # Dummy static growth
        })
    
    return jsonify({"lead_report": report})

@reports_bp.route('/sales', methods=['GET'])
def get_sales_metrics():
    won = Deal.query.filter(text("status = 'won'")).count()
    lost = Deal.query.filter(text("status = 'lost'")).count()
    
    avg_deal = db.session.query(func.avg(Deal.value)).scalar() or 0
    
    top_deals = Deal.query.filter(text("status = 'won'"))\
        .order_by(desc(Deal.value)).limit(5).all()
        
    return jsonify({
        "won_deals": won,
        "lost_deals": lost,
        "average_deal_size": int(avg_deal),
        "top_deals": [{
            "title": d.title,
            "value": d.value,
            "owner": d.owner
        } for d in top_deals]
    })

@reports_bp.route('/reps', methods=['GET'])
def get_reps_performance():
    # Group by Owner and fetch target from users table
    # Using raw SQL to ensure we get the target column which might be added via seed script
    sql = text("""
        SELECT d.owner, SUM(d.value) as revenue, COUNT(d.id) as deals_won, COALESCE(u.target, 0) as target
        FROM deals d
        LEFT JOIN users u ON d.owner = u.name
        WHERE d.status = 'won'
        GROUP BY d.owner, u.target
    """)
    
    results = db.session.execute(sql).fetchall()

    data = []
    for r in results:
        target = r[3] or 0
        revenue = int(r[1] or 0)
        achievement = round((revenue / target * 100), 1) if target > 0 else 0
        
        data.append({
            "name": r[0],
            "revenue": revenue,
            "deals_won": r[2],
            "target": target,
            "achievement": achievement
        })
    return jsonify(data)

@reports_bp.route('/pipeline', methods=['GET'])
def get_pipeline_overview():
    results = db.session.query(
        Deal.stage,
        func.sum(Deal.value),
        func.count(Deal.id)
    ).filter(text("status = 'open'")).group_by(Deal.stage).all()

    return jsonify([{
        "stage": r[0],
        "value": int(r[1] or 0),
        "count": r[2],
        "avg_days": 12 # Mock avg time in stage
    } for r in results])