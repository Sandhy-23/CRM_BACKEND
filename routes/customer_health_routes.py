from flask import Blueprint, jsonify, request
from extensions import db
from models.contact import Contact
from models.ticket import Ticket
from models.feedback import Feedback
from models.customer_health import CustomerHealth
from routes.auth_routes import token_required
from sqlalchemy import func, case
from datetime import datetime

customer_health_bp = Blueprint('customer_health', __name__)

# --- Helper Functions ---

def calculate_nps(contact_id):
    """Calculates average rating for a contact."""
    ratings = Feedback.query.filter_by(contact_id=contact_id).all()
    if not ratings:
        return 0
    avg = sum(r.rating for r in ratings) / len(ratings)
    return round(avg, 1)

def get_open_tickets(contact_id):
    """Counts open tickets for a contact."""
    return Ticket.query.filter(
        Ticket.contact_id == contact_id,
        Ticket.status.in_(['Open', 'In Progress', 'Pending'])
    ).count()

def get_sla_breaches(contact_id):
    """Counts SLA breaches for a contact."""
    return Ticket.query.filter_by(
        contact_id=contact_id,
        sla_breached=True
    ).count()

def get_health_status(score):
    """Determines status based on score."""
    if score >= 80:
        return "Healthy"
    elif score >= 50:
        return "At Risk"
    else:
        return "Churn Risk"

def calculate_trend(current_score, previous_score):
    """Calculates percentage trend."""
    if not previous_score:
        return 0.0
    return round(((current_score - previous_score) / previous_score) * 100, 1)

# --- Dashboard API ---

@customer_health_bp.route('/api/customer-health/dashboard', methods=['GET'])
@token_required
def get_dashboard(current_user):
    # 1. Fetch all contacts for the organization
    contacts = Contact.query.filter_by(organization_id=current_user.organization_id, is_deleted=False).all()
    
    customers_data = []
    health_distribution = {"Healthy": 0, "At Risk": 0, "Churn Risk": 0}
    total_customers = len(contacts)
    churn_risk_count = 0

    for c in contacts:
        # Calculate Metrics
        nps = calculate_nps(c.id)
        open_tickets = get_open_tickets(c.id)
        sla = get_sla_breaches(c.id)

        # Calculate Health Score
        # Formula: (NPS * 4) - (Open Tickets * 5) - (SLA Breaches * 10)
        score = int((nps * 4) - (open_tickets * 5) - (sla * 10))

        status = get_health_status(score)
        
        # Update Distribution
        health_distribution[status] += 1
        if status == "Churn Risk":
            churn_risk_count += 1

        # Check for previous health record to calculate trend
        prev_health = CustomerHealth.query.filter_by(contact_id=c.id).order_by(CustomerHealth.updated_at.desc()).first()
        trend = calculate_trend(score, prev_health.health_score) if prev_health else 0.0

        # Save/Update Health Record
        # In a real system, you might run this via a cron job daily, not on every GET request.
        # For this implementation, we calculate on the fly and update.
        if not prev_health or prev_health.health_score != score:
            new_health = CustomerHealth(
                contact_id=c.id,
                health_score=score,
                health_status=status,
                trend=trend,
                updated_at=datetime.utcnow()
            )
            db.session.add(new_health)
            db.session.commit()

        customers_data.append({
            "id": c.id,
            "customer": c.company or c.name,
            "plan": c.plan_type,
            "health_score": score,
            "health_status": status,
            "trend": trend,
            "nps": nps,
            "open_tickets": open_tickets,
            "sla_breaches": sla
        })

    # 2. NPS Breakdown
    # Aggregating all feedback for the organization
    nps_stats = db.session.query(
        func.sum(case((Feedback.rating >= 9, 1), else_=0)).label('promoters'),
        func.sum(case((Feedback.rating.between(7, 8), 1), else_=0)).label('passives'),
        func.sum(case((Feedback.rating <= 6, 1), else_=0)).label('detractors'),
        func.count(Feedback.id).label('total')
    ).join(Contact, Feedback.contact_id == Contact.id).filter(Contact.organization_id == current_user.organization_id).first()

    nps_breakdown = {
        "Promoters": 0, "Passives": 0, "Detractors": 0
    }
    if nps_stats and nps_stats.total > 0:
        nps_breakdown["Promoters"] = round((nps_stats.promoters / nps_stats.total) * 100, 1)
        nps_breakdown["Passives"] = round((nps_stats.passives / nps_stats.total) * 100, 1)
        nps_breakdown["Detractors"] = round((nps_stats.detractors / nps_stats.total) * 100, 1)

    # 3. Churn Risk Percentage
    churn_risk_pct = round((churn_risk_count / total_customers * 100), 1) if total_customers > 0 else 0

    return jsonify({
        "customers": customers_data,
        "health_distribution": health_distribution,
        "nps_breakdown": nps_breakdown,
        "churn_risk": {"percentage": churn_risk_pct, "count": churn_risk_count}
    })