from extensions import db
from datetime import datetime

class Contact(db.Model):
    __tablename__ = "contacts"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    company = db.Column(db.String(120))
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    owner = db.Column(db.String(50))
    last_contact = db.Column(db.String(50))
    status = db.Column(db.String(20))