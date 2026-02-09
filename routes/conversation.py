from extensions import db
from datetime import datetime
import uuid

class Conversation(db.Model):
    __tablename__ = 'conversations'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    channel = db.Column(db.String(50), nullable=False) # whatsapp, email, etc.
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'))
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'))
    status = db.Column(db.String(20), default='open')
    last_message_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'))

    lead = db.relationship('Lead', backref='conversations')
    assignee = db.relationship('User', backref='conversations')
    messages = db.relationship('Message', backref='conversation', lazy=True, order_by="Message.created_at")