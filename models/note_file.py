from extensions import db
from datetime import datetime

class Note(db.Model):
    """
    Represents a note in the system.
    The 'note' column holds the full text content.
    'title' is not a database column and should be derived in the API.
    """
    __tablename__ = 'notes'

    id = db.Column(db.Integer, primary_key=True)
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class File(db.Model):
    """Represents an uploaded file."""
    __tablename__ = 'files'

    id = db.Column(db.Integer, primary_key=True)
    entity_type = db.Column(db.String(50), index=True)
    entity_id = db.Column(db.Integer, index=True)
    file_name = db.Column(db.String(255))
    file_path = db.Column(db.String(255))
    file_size = db.Column(db.Integer)
    file_type = db.Column(db.String(100))
    uploaded_by = db.Column(db.Integer)
    company_id = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Serializes the object to a dictionary."""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}