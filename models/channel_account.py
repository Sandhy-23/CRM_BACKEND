from extensions import db
from datetime import datetime


class ChannelAccount(db.Model):
    __tablename__ = "channel_accounts"

    id = db.Column(db.Integer, primary_key=True)

    channel = db.Column(db.String(50), nullable=False)
    # whatsapp / email / instagram / facebook

    business_id = db.Column(db.String(255), nullable=True)
    phone_number_id = db.Column(db.String(255), nullable=True)

    access_token = db.Column(db.Text, nullable=True)
    webhook_secret = db.Column(db.String(255), nullable=True)

    is_active = db.Column(db.Boolean, default=True)

    organization_id = db.Column(db.Integer, nullable=True)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )