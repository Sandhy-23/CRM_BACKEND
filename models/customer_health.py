from extensions import db
from datetime import datetime

class CustomerHealth(db.Model):
    __tablename__ = 'customer_health'

    id = db.Column(db.Integer, primary_key=True)
    contact_id = db.Column(db.Integer, db.ForeignKey('contacts.id'))
    health_score = db.Column(db.Integer)
    health_status = db.Column(db.String(50)) # Healthy, At Risk, Churn Risk
    trend = db.Column(db.Float, default=0.0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    contact = db.relationship('Contact', backref='health_metrics')