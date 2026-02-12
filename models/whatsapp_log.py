from extensions import db
from datetime import datetime

class WhatsAppCampaignLog(db.Model):
    __tablename__ = "whatsapp_campaign_logs"

    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.String(50), nullable=False)
    lead_id = db.Column(db.Integer, nullable=True)
    phone = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default="sent")
    error_message = db.Column(db.Text, nullable=True)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    organization_id = db.Column(db.Integer, nullable=False)