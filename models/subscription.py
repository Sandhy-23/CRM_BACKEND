from extensions import db
from datetime import datetime

class Subscription(db.Model):
    __tablename__ = "subscriptions"

    id = db.Column(db.Integer, primary_key=True)

    organization_id = db.Column(db.Integer)
    plan_id = db.Column(db.Integer)

    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)

    status = db.Column(db.String(50))
    is_trial = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)