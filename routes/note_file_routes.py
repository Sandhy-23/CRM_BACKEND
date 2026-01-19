from flask import Blueprint, request, jsonify, send_file, current_app
from extensions import db
from routes.auth_routes import token_required
from models.note_file import Note, File
from models.crm import Lead, Deal
from models.contact import Contact
from models.user import User
import os
from werkzeug.utils import secure_filename
from datetime import datetime

note_file_bp = Blueprint('note_files', __name__)

# --- Configuration ---
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx', 'xls', 'xlsx'}
MAX_FILE_SIZE = 10 * 1024 * 1024 # 10MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Helper: RBAC & Entity Validation ---
def get_entity_config(entity_type):
    """Maps entity type to Model and its owner/org fields."""
    if entity_type == 'lead':
        return Lead, 'owner_id', 'company_id'
    elif entity_type == 'contact':
        return Contact, 'assigned_to', 'organization_id'
    elif entity_type == 'deal':
        return Deal, 'owner_id', 'company_id'
    return None, None, None

def validate_access(user, entity_type, entity_id):
    """
    Validates if the user has access to the specific entity based on Role and Company.
    Returns (entity_object, error_message).
    """
    model, owner_field, org_field = get_entity_config(entity_type)
    
    if not model:
        return None, "Invalid entity type. Must be lead, contact, or deal."

    entity = model.query.get(entity_id)
    if not entity:
        return None, "Entity not found."

    # 1. Organization Isolation (Cross-Company Check)
    entity_org_id = getattr(entity, org_field)
    # Note: Super Admin can access any org, but usually acts within context. 
    # Assuming Super Admin has global access, others restricted to their org.
    if user.role != 'SUPER_ADMIN' and entity_org_id != user.organization_id:
        return None, "Permission denied. You cannot access records from another organization."

    # 2. Role-Based Access
    if user.role in ['SUPER_ADMIN', 'ADMIN']:
        return entity, None

    if user.role == 'MANAGER':
        # Manager sees team data (Same Department)
        owner_id = getattr(entity, owner_field)
        if owner_id == user.id:
            return entity, None
            
        owner = User.query.get(owner_id)
        if owner and owner.department == user.department and owner.organization_id == user.organization_id:
            return entity, None
        return None, "Permission denied. Record not in your team."

    if user.role in ['EMPLOYEE', 'USER']:
        # Employee sees only assigned records
        owner_id = getattr(entity, owner_field)
        if owner_id == user.id:
            return entity, None
        return None, "Permission denied. You are not assigned to this record."

    return None, "Permission denied."

# --- NOTES APIs ---

@note_file_bp.route('/api/notes', methods=['POST'])
@token_required
def create_note(current_user):
    data = request.get_json()
    entity_type = data.get('entity_type', '').lower()
    entity_id = data.get('entity_id')
    note_text = data.get('note_text')

    if not note_text:
        return jsonify({'error': 'Validation Error', 'message': 'Note text is required'}), 400

    # Validate Access
    entity, error = validate_access(current_user, entity_type, entity_id)
    if error:
        return jsonify({'error': 'Permission denied', 'message': error}), 403

    # Determine Company ID
    # Prioritize entity's organization. If None (e.g. global entity), try user's org. If both None, use 0.
    _, _, org_field = get_entity_config(entity_type)
    entity_org_id = getattr(entity, org_field)
    
    if entity_org_id:
        company_id = entity_org_id
    else:
        company_id = current_user.organization_id if current_user.organization_id else 0

    new_note = Note(
        entity_type=entity_type,
        entity_id=entity_id,
        note_text=note_text,
        created_by=current_user.id,
        company_id=company_id
    )
    
    db.session.add(new_note)
    db.session.commit()
    
    return jsonify({'message': 'Note added successfully', 'note': new_note.to_dict()}), 201

@note_file_bp.route('/api/notes', methods=['GET'])
@token_required
def get_notes(current_user):
    entity_type = request.args.get('entity_type', '').lower()
    entity_id = request.args.get('entity_id')

    if not entity_type or not entity_id:
        return jsonify({'error': 'Validation Error', 'message': 'entity_type and entity_id are required'}), 400

    # Validate Access
    entity, error = validate_access(current_user, entity_type, entity_id)
    if error:
        return jsonify({'error': 'Permission denied', 'message': error}), 403

    notes = Note.query.filter_by(entity_type=entity_type, entity_id=entity_id)\
        .order_by(Note.created_at.desc()).all()
        
    return jsonify([n.to_dict() for n in notes]), 200

@note_file_bp.route('/api/notes/<int:note_id>', methods=['DELETE'])
@token_required
def delete_note(current_user, note_id):
    note = Note.query.get(note_id)
    if not note:
        return jsonify({'error': 'Not Found', 'message': 'Note not found'}), 404

    # Security: Ensure user belongs to the same company as the note
    if current_user.role != 'SUPER_ADMIN' and note.company_id != current_user.organization_id:
        return jsonify({'error': 'Permission denied', 'message': 'Unauthorized access'}), 403

    # Permission: Only Creator, Admin, or Super Admin
    if current_user.role not in ['SUPER_ADMIN', 'ADMIN'] and note.created_by != current_user.id:
        return jsonify({'error': 'Permission denied', 'message': 'Only the creator or Admin can delete this note'}), 403

    db.session.delete(note)
    db.session.commit()
    return jsonify({'message': 'Note deleted successfully'}), 200

# --- FILES APIs ---

@note_file_bp.route('/api/files', methods=['POST'])
@token_required
def upload_file(current_user):
    if 'file' not in request.files:
        return jsonify({'error': 'Validation Error', 'message': 'No file part'}), 400
        
    file = request.files['file']
    entity_type = request.form.get('entity_type', '').lower()
    entity_id = request.form.get('entity_id')

    if file.filename == '':
        return jsonify({'error': 'Validation Error', 'message': 'No selected file'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Validation Error', 'message': 'File type not allowed'}), 400

    # Validate Access
    entity, error = validate_access(current_user, entity_type, entity_id)
    if error:
        return jsonify({'error': 'Permission denied', 'message': error}), 403

    # Determine Company ID (Use entity's org ID to ensure correct storage bucket)
    _, _, org_field = get_entity_config(entity_type)
    entity_org_id = getattr(entity, org_field)
    
    # Fallback to 0 if no company associated (e.g. Super Admin global data)
    company_id = entity_org_id if entity_org_id else (current_user.organization_id if current_user.organization_id else 0)

    # Prepare Storage Path: /uploads/{company_id}/{entity_type}/
    filename = secure_filename(file.filename)
    upload_folder = os.path.join(os.getcwd(), 'uploads', str(company_id), entity_type)
    
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
        
    file_path = os.path.join(upload_folder, filename)
    
    # Check File Size (Manual check if not handled by Nginx/Flask config)
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    
    if size > MAX_FILE_SIZE:
        return jsonify({'error': 'Validation Error', 'message': 'File too large (Max 10MB)'}), 400

    # Save File
    file.save(file_path)

    # Save Metadata
    new_file = File(
        entity_type=entity_type,
        entity_id=entity_id,
        file_name=filename,
        file_path=file_path,
        file_size=size,
        file_type=file.content_type,
        uploaded_by=current_user.id,
        company_id=company_id
    )
    
    db.session.add(new_file)
    db.session.commit()
    
    return jsonify({'message': 'File uploaded successfully', 'file': new_file.to_dict()}), 201

@note_file_bp.route('/api/files', methods=['GET'])
@token_required
def get_files(current_user):
    entity_type = request.args.get('entity_type', '').lower()
    entity_id = request.args.get('entity_id')

    if not entity_type or not entity_id:
        return jsonify({'error': 'Validation Error', 'message': 'entity_type and entity_id are required'}), 400

    entity, error = validate_access(current_user, entity_type, entity_id)
    if error:
        return jsonify({'error': 'Permission denied', 'message': error}), 403

    files = File.query.filter_by(entity_type=entity_type, entity_id=entity_id)\
        .order_by(File.created_at.desc()).all()
        
    return jsonify([f.to_dict() for f in files]), 200

@note_file_bp.route('/api/files/<int:file_id>/download', methods=['GET'])
@token_required
def download_file(current_user, file_id):
    file_record = File.query.get(file_id)
    if not file_record:
        return jsonify({'error': 'Not Found', 'message': 'File record not found'}), 404

    # Validate Access to the parent entity to ensure permission still holds
    _, error = validate_access(current_user, file_record.entity_type, file_record.entity_id)
    if error:
        return jsonify({'error': 'Permission denied', 'message': error}), 403

    if not os.path.exists(file_record.file_path):
        return jsonify({'error': 'Not Found', 'message': 'File not found on server'}), 404

    return send_file(file_record.file_path, as_attachment=True, download_name=file_record.file_name)

@note_file_bp.route('/api/files/<int:file_id>', methods=['DELETE'])
@token_required
def delete_file(current_user, file_id):
    file_record = File.query.get(file_id)
    if not file_record:
        return jsonify({'error': 'Not Found', 'message': 'File record not found'}), 404

    # Security: Company Check
    if current_user.role != 'SUPER_ADMIN' and file_record.company_id != current_user.organization_id:
        return jsonify({'error': 'Permission denied', 'message': 'Unauthorized access'}), 403

    # Permission: Only Uploader, Admin, or Super Admin
    if current_user.role not in ['SUPER_ADMIN', 'ADMIN'] and file_record.uploaded_by != current_user.id:
        return jsonify({'error': 'Permission denied', 'message': 'Only the uploader or Admin can delete this file'}), 403

    # Remove from Disk
    if os.path.exists(file_record.file_path):
        try:
            os.remove(file_record.file_path)
        except Exception as e:
            print(f"Error deleting file from disk: {e}")

    db.session.delete(file_record)
    db.session.commit()
    
    return jsonify({'message': 'File deleted successfully'}), 200