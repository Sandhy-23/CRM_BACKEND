from extensions import db
from datetime import datetime

class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'

    id = db.Column(db.Integer, primary_key=True)
    module = db.Column(db.String(50), nullable=False)
    action = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)

    related_id = db.Column(db.Integer)

    user_id = db.Column(db.Integer, nullable=False)
    company_id = db.Column(db.Integer, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='activity_logs', primaryjoin='foreign(ActivityLog.user_id) == User.id')

    def to_dict(self):
        return {
            "id": self.id,
            "module": self.module,
            "action": self.action,
            "description": self.description,
            "related_id": self.related_id,
            "user": self.user.name if self.user else "Unknown",
            "created_at": self.created_at.isoformat() if self.created_at else None
        }