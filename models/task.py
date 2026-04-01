from extensions import db
from datetime import datetime

class Task(db.Model):
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='pending')
    
    priority = db.Column(db.String(20), default="medium")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    due_date = db.Column(db.Date, nullable=True)

    # Relationships
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_tasks')

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "due_date": self.due_date.strftime('%Y-%m-%d') if self.due_date else None
        }