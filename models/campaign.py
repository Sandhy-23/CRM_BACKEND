from extensions import db
from datetime import datetime
import uuid

class Campaign(db.Model):
    __tablename__ = 'campaigns'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(255), nullable=False)
    channel = db.Column(db.String(50)) # email, whatsapp
    status = db.Column(db.String(50), default='Draft')
    scheduled_at = db.Column(db.DateTime)
    organization_id = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)