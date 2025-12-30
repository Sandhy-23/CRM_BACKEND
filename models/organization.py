from extensions import db
from datetime import datetime

class Organization(db.Model):
    __tablename__ = "organizations"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, default="My Organization")
    subscription_plan = db.Column(db.String(50), default="Free")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    plan_id = db.Column(db.Integer, db.ForeignKey('plans.id'), nullable=True)
    plan = db.relationship('Plan')
    
    users = db.relationship('User', backref='organization', lazy=True)