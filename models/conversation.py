from extensions import db
from datetime import datetime

class Conversation(db.Model):
    __tablename__ = "conversations"

    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, nullable=True)
    channel = db.Column(db.String(50))   # whatsapp, email, instagram
    assigned_to = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(20), default="open")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)