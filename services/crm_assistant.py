from sqlalchemy import func
from extensions import db
from models.crm import Lead, Deal

def process_message(message):
    msg = message.lower()

    # TOTAL LEADS
    if "total leads" in msg:
        total = db.session.query(func.count(Lead.id)).scalar() or 0
        return f"You have {total} total leads."

    # TODAY LEADS
    elif "today leads" in msg:
        # SQLite compatible date check
        total = db.session.query(func.count(Lead.id)) \
            .filter(func.date(Lead.created_at) == func.date(func.now())) \
            .scalar() or 0
        return f"You have {total} leads today."

    # TOTAL REVENUE
    elif "revenue" in msg:
        revenue = db.session.query(func.sum(Deal.value)) \
            .filter(Deal.status == "won") \
            .scalar() or 0
        return f"Total revenue from won deals is {int(revenue)}."

    # WON DEALS
    elif "won deals" in msg:
        count = db.session.query(func.count(Deal.id)) \
            .filter(Deal.status == "won") \
            .scalar() or 0
        return f"You have {count} won deals."

    # BEST PERFORMER
    elif "best performer" in msg:
        result = db.session.query(
            Deal.owner,
            func.sum(Deal.value)
        ).filter(Deal.status == "won") \
         .group_by(Deal.owner) \
         .order_by(func.sum(Deal.value).desc()) \
         .first()

        if result:
            return f"Top performer is {result[0]} with revenue {int(result[1])}."
        else:
            return "No performance data available."

    else:
        return "I didn't understand. You can ask about 'total leads', 'revenue', 'won deals', or 'best performer'."