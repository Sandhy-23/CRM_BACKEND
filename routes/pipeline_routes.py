from flask import Blueprint, request, jsonify
from extensions import db
from models.pipeline import Pipeline, PipelineStage
from routes.auth_routes import token_required

pipeline_bp = Blueprint('pipelines', __name__)

@pipeline_bp.route('/pipelines', methods=['POST'])
@token_required
def create_pipeline(current_user):
    if current_user.role not in ['SUPER_ADMIN', 'ADMIN']:
        return jsonify({'message': 'Unauthorized'}), 403
        
    data = request.get_json()
    name = data.get('name')
    
    if not name:
        return jsonify({'message': 'Pipeline name is required'}), 400
        
    new_pipeline = Pipeline(
        name=name,
        company_id=current_user.organization_id,
        is_default=False
    )
    
    db.session.add(new_pipeline)
    db.session.commit()
    
    return jsonify({'message': 'Pipeline created', 'id': new_pipeline.id, 'name': new_pipeline.name}), 201

@pipeline_bp.route('/pipelines/<int:pipeline_id>/stages', methods=['POST'])
@token_required
def add_stages(current_user, pipeline_id):
    if current_user.role not in ['SUPER_ADMIN', 'ADMIN']:
        return jsonify({'message': 'Unauthorized'}), 403
        
    pipeline = Pipeline.query.filter_by(id=pipeline_id, company_id=current_user.organization_id).first()
    if not pipeline:
        return jsonify({'message': 'Pipeline not found'}), 404
        
    data = request.get_json()
    stage_names = data.get('stages', [])
    
    if not stage_names or not isinstance(stage_names, list):
        return jsonify({'message': 'List of stages is required'}), 400
        
    current_max = PipelineStage.query.filter_by(pipeline_id=pipeline.id).count()
    
    new_stages = []
    for i, name in enumerate(stage_names):
        stage = PipelineStage(
            pipeline_id=pipeline.id,
            name=name,
            stage_order=current_max + i + 1
        )
        new_stages.append(stage)
        
    db.session.add_all(new_stages)
    db.session.commit()
    
    return jsonify({'message': f'{len(new_stages)} stages added'}), 201

@pipeline_bp.route('/pipelines', methods=['GET'])
@token_required
def get_pipelines(current_user):
    pipelines = Pipeline.query.filter_by(company_id=current_user.organization_id).all()
    
    result = []
    for p in pipelines:
        stages = PipelineStage.query.filter_by(pipeline_id=p.id).order_by(PipelineStage.stage_order).all()
        result.append({
            "id": p.id,
            "name": p.name,
            "is_default": p.is_default,
            "stages": [{"id": s.id, "name": s.name, "order": s.stage_order} for s in stages]
        })
        
    return jsonify(result), 200