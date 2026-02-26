from extensions import db
from datetime import datetime

class Organization(db.Model):
    __tablename__ = "organizations"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, default="My Organization")
    subscription_plan = db.Column(db.String(50), default="Free")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Organization Details
    company_size = db.Column(db.String(50))
    industry = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    country = db.Column(db.String(100))
    state = db.Column(db.String(100))
    city_or_branch = db.Column(db.String(100))
    website = db.Column(db.String(150))
    address = db.Column(db.String(250))
    total_employees = db.Column(db.Integer)
    founded_year = db.Column(db.String(10))
    hq = db.Column(db.String(100))
    legal_name = db.Column(db.String(150))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    plan_id = db.Column(db.Integer, db.ForeignKey('plans.id'), nullable=True)
    plan = db.relationship('Plan')
    
    users = db.relationship('User', foreign_keys='User.organization_id', backref='organization', lazy=True)