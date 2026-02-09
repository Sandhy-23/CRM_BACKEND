from extensions import db
from datetime import datetime
import uuid

class Message(db.Model):
    __tablename__ = 'messages'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = db.Column(db.String(36), db.ForeignKey('conversations.id'), nullable=False)
    channel = db.Column(db.String(50), nullable=False)
    sender_type = db.Column(db.String(20)) # customer / agent
    content = db.Column(db.Text)
    status = db.Column(db.String(20), default='sent') # sent / delivered / read
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "sender_type": self.sender_type,
            "content": self.content,
            "status": self.status,
            "created_at": self.created_at.isoformat()
        }