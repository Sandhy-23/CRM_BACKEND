from extensions import db
from datetime import datetime

class Pipeline(db.Model):
    __tablename__ = 'pipelines'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    company_id = db.Column(db.Integer, nullable=False)
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    stages = db.relationship('PipelineStage', backref='pipeline', cascade="all, delete-orphan", order_by='PipelineStage.stage_order')

class PipelineStage(db.Model):
    __tablename__ = 'pipeline_stages'
    id = db.Column(db.Integer, primary_key=True)
    pipeline_id = db.Column(db.Integer, db.ForeignKey('pipelines.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    stage_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)