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

class Conversation(db.Model):
    __tablename__ = "conversations"

    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'), nullable=False)
    channel = db.Column(db.String(50), default='whatsapp')
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'))
    company_id = db.Column(db.Integer) # Required for multi-tenancy checks in routes
    state = db.Column(db.String(100))
    unread_count = db.Column(db.Integer, default=0)
    last_message_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships required by routes/whatsapp_routes.py
    lead = db.relationship('Lead', backref='conversations')
    assignee = db.relationship('User', backref='conversations')

class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversations.id'), nullable=False)
    direction = db.Column(db.String(20))  # incoming / outgoing
    message_type = db.Column(db.String(20))  # text / image
    content = db.Column(db.Text)
    status = db.Column(db.String(20))  # sent / delivered / read
    whatsapp_message_id = db.Column(db.String(100)) # Required for webhook status updates
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    conversation = db.relationship('Conversation', backref='messages')

    def to_dict(self):
        return {
            "id": self.id,
            "direction": self.direction,
            "content": self.content,
            "status": self.status,
            "created_at": self.created_at.isoformat()
        }