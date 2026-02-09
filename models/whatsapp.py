from extensions import db
from datetime import datetime

class WhatsAppAccount(db.Model):
    __tablename__ = "whatsapp_accounts"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, nullable=False)
    business_id = db.Column(db.String(255))
    phone_number_id = db.Column(db.String(255))
    access_token = db.Column(db.Text)
    webhook_secret = db.Column(db.String(255))
    status = db.Column(db.String(50), default="connected")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)