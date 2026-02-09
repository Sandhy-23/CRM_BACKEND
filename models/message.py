from extensions import db
from datetime import datetime


class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)

    conversation_id = db.Column(
        db.Integer,
        db.ForeignKey("conversations.id"),
        nullable=False
    )

    sender_type = db.Column(db.String(20))  
    # agent / customer / system

    sender_id = db.Column(db.Integer, nullable=True)

    content = db.Column(db.Text, nullable=False)

    status = db.Column(
        db.String(20),
        default="sent"
    )  
    # sending / sent / delivered / read

    channel = db.Column(db.String(50))  
    # whatsapp / email / instagram

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )