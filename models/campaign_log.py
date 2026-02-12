from extensions import db
from datetime import datetime

class CampaignLog(db.Model):
    __tablename__ = 'campaign_logs'

    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.String(36), db.ForeignKey('campaigns.id'), nullable=False)
    contact_id = db.Column(db.Integer, nullable=True) # ID of the lead/contact
    status = db.Column(db.String(20), nullable=False) # sent / failed
    channel = db.Column(db.String(50), nullable=False)
    opened = db.Column(db.Boolean, default=False)
    clicked = db.Column(db.Boolean, default=False)
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)