from datetime import datetime, timedelta
from models.sla_rule import SLARule

def calculate_sla_due(ticket):
    rule = SLARule.query.filter_by(priority=ticket.priority).first()

    if not rule:
        return None

    return datetime.utcnow() + timedelta(hours=rule.resolution_time_hours)