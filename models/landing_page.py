from extensions import db
from datetime import datetime
import uuid


class LandingPage(db.Model):
    __tablename__ = "landing_pages"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), unique=True, nullable=False)
    campaign = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), default="Draft")
    
    leads = db.Column(db.Integer, default=0)
    conversion = db.Column(db.String(20), default="0%")
    visitors = db.Column(db.Integer, default=0)

    headline = db.Column(db.Text, nullable=True)
    description = db.Column(db.Text, nullable=True)
    form_fields = db.Column(db.JSON, nullable=True)

    organization_id = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)