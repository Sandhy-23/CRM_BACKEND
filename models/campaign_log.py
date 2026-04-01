from extensions import db
from datetime import datetime

class CampaignLog(db.Model):
    __tablename__ = 'campaign_logs'

    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.String(36), db.ForeignKey('campaigns.id'))
    contact_id = db.Column(db.Integer) # or Lead ID
    status = db.Column(db.String(50))
    channel = db.Column(db.String(50))
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)