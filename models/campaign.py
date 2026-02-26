from extensions import db
import json
from datetime import datetime
import uuid

class Campaign(db.Model):
    __tablename__ = "campaigns"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(255), nullable=False)
    channel = db.Column(db.String(50), nullable=False) # Email | WhatsApp | Social
    status = db.Column(db.String(50), default='Draft') # Draft | Running | Scheduled | Completed | Failed
    month = db.Column(db.Integer)
    year = db.Column(db.Integer)
    color = db.Column(db.String(20), default="blue")
    branch = db.Column(db.String(100), nullable=True)
    config = db.Column(db.JSON, nullable=True)
    whatsapp_config = db.Column(db.JSON, nullable=True)
    start_date = db.Column(db.DateTime, nullable=True)
    end_date = db.Column(db.DateTime, nullable=True)
    budget = db.Column(db.Float, default=0.0)
    spent = db.Column(db.Float, default=0.0)
    scheduled_at = db.Column(db.DateTime, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)