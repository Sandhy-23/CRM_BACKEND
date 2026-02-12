from extensions import db
from datetime import datetime

class DripCampaign(db.Model):
    __tablename__ = 'drip_campaigns'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(50), default='draft', nullable=False) # draft / active / paused
    audience_type = db.Column(db.String(50), nullable=False) # all / tag / new_leads
    audience_value = db.Column(db.String(255)) # e.g., tag name
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    steps = db.relationship('DripStep', backref='campaign', lazy=True, cascade="all, delete-orphan", order_by="DripStep.step_number")
    enrollments = db.relationship('DripEnrollment', backref='campaign', lazy=True, cascade="all, delete-orphan")

class DripStep(db.Model):
    __tablename__ = 'drip_steps'
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('drip_campaigns.id'), nullable=False)
    step_number = db.Column(db.Integer, nullable=False)
    delay_days = db.Column(db.Integer, default=0, nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class DripEnrollment(db.Model):
    __tablename__ = 'drip_enrollments'
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('drip_campaigns.id'), nullable=False)
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'), nullable=False)
    current_step = db.Column(db.Integer, default=1, nullable=False)
    status = db.Column(db.String(50), default='active', nullable=False) # active / completed / stopped
    next_send_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    lead = db.relationship('Lead', backref='drip_enrollments')