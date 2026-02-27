from extensions import db
from datetime import datetime

class Call(db.Model):
    __tablename__ = 'call_logs'

    id = db.Column(db.Integer, primary_key=True)
    customer_number = db.Column(db.String(20))
    direction = db.Column(db.String(20)) # 'incoming' or 'outgoing'
    status = db.Column(db.String(50))
    call_sid = db.Column(db.String(100))
    duration = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "customer_number": self.customer_number,
            "direction": self.direction,
            "status": self.status,
            "call_sid": self.call_sid,
            "duration": self.duration,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }