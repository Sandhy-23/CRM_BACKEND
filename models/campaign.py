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
    config = db.Column(db.Text, nullable=True)
    scheduled_at = db.Column(db.DateTime, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)