from extensions import db
from datetime import datetime

class ChatMessage(db.Model):
    __tablename__ = "chat_messages"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    sender = db.Column(db.String(20))  # user / bot
    message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)