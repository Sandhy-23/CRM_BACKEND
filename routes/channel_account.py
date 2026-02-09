from extensions import db
from datetime import datetime

class ChannelAccount(db.Model):
    __tablename__ = 'channel_accounts'
    
    id = db.Column(db.Integer, primary_key=True)
    channel = db.Column(db.String(50), nullable=False)
    account_name = db.Column(db.String(100))
    access_token = db.Column(db.Text)
    credentials = db.Column(db.JSON) # Store extra config like business_id, secret
    status = db.Column(db.String(20), default='connected')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'))