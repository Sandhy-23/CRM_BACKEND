from extensions import db
from datetime import datetime


class LandingPage(db.Model):
    __tablename__ = "landing_pages"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), unique=True, nullable=False)
    branch_id = db.Column(db.Integer, nullable=False)
    campaign_id = db.Column(db.String(50), nullable=True)
    is_published = db.Column(db.Boolean, default=False)
    organization_id = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class LandingPageForm(db.Model):
    __tablename__ = "landing_page_forms"

    id = db.Column(db.Integer, primary_key=True)
    landing_page_id = db.Column(db.Integer, nullable=False)
    fields = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class FormSubmission(db.Model):
    __tablename__ = "form_submissions"

    id = db.Column(db.Integer, primary_key=True)
    form_id = db.Column(db.Integer, nullable=False)
    data = db.Column(db.JSON, nullable=False)
    ip_address = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class LandingPageEvent(db.Model):
    __tablename__ = "landing_page_events"

    id = db.Column(db.Integer, primary_key=True)
    landing_page_id = db.Column(db.Integer, nullable=False)
    event_type = db.Column(db.String(50))  # view / conversion
    created_at = db.Column(db.DateTime, default=datetime.utcnow)