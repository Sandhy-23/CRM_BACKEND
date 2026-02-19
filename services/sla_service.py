from datetime import datetime, timedelta


def calculate_sla_due(ticket):
    """
    Calculate SLA due time based on priority.
    """
    priority = getattr(ticket, 'priority', "medium").lower()

    now = datetime.utcnow()

    if priority == "high":
        return now + timedelta(hours=4)
    elif priority == "medium":
        return now + timedelta(hours=8)
    elif priority == "low":
        return now + timedelta(hours=24)
    else:
        return now + timedelta(hours=8)