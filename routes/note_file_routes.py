from flask import Blueprint, request, jsonify, send_file, current_app, send_from_directory
from extensions import db
from routes.auth_routes import token_required
from models.note_file import Note, File
from models.crm import Lead, Deal
from models.contact import Contact
from models.user import User
import os
from werkzeug.utils import secure_filename
from datetime import datetime
from models.activity_logger import log_activity

note_file_bp = Blueprint('note_files', __name__)

# --- Configuration ---
UPLOAD_FOLDER = "uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# --- Helper: RBAC & Entity Validation ---
def get_entity_config(entity_type):
    """Maps entity type to Model and its owner/org fields."""
    if entity_type == 'lead':
        return Lead, 'owner', None
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
    if org_field:
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
        if entity_type == 'lead':
            # Lead uses string owner name, strict ID check not possible
            if getattr(entity, owner_field) == user.name:
                return entity, None
            return None, "Permission denied. You are not assigned to this record."

        owner_id = getattr(entity, owner_field)
        if owner_id == user.id:
            return entity, None
            
        owner = User.query.get(owner_id)
        if owner and owner.department == user.department and owner.organization_id == user.organization_id:
            return entity, None
        return None, "Permission denied. Record not in your team."

    if user.role in ['EMPLOYEE', 'USER']:
        if entity_type == 'lead':
            # Lead uses string owner name
            if getattr(entity, owner_field) == user.name:
                return entity, None
            return None, "Permission denied. You are not assigned to this record."

        # Employee sees only assigned records
        owner_id = getattr(entity, owner_field)
        if owner_id == user.id:
            return entity, None
        return None, "Permission denied. You are not assigned to this record."

    return None, "Permission denied."

# --- NOTES APIs ---

@note_file_bp.route("/notes", methods=["POST"])
@token_required
def add_note(current_user):
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid or missing JSON body"}), 400

        title = data.get("title")
        note_text = data.get("note") or data.get("content")

        if not note_text:
            return jsonify({"error": "Note is required"}), 400

        # Create Note with explicit mapping
        new_note = Note(title=title, note=note_text)
        
        db.session.add(new_note)
        db.session.commit()

        return jsonify({"message": "Note added", "id": new_note.id}), 201
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Failed to add note: {str(e)}")
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500

@note_file_bp.route('/notes', methods=['GET'])
@token_required
def get_notes(current_user):
    notes = Note.query.order_by(Note.created_at.desc()).all()

    return jsonify([
        {
            "id": n.id,
            "title": n.title,
            "note": n.note,
            "created_at": n.created_at
        }
        for n in notes
    ])

@note_file_bp.route('/notes/<int:note_id>', methods=['DELETE'])
@token_required
def delete_note(current_user, note_id):
    note = Note.query.get(note_id)

    if not note:
        return jsonify({"error": "Note not found"}), 404

    db.session.delete(note)
    db.session.commit()

    return jsonify({"message": "Note deleted successfully"})

@note_file_bp.route("/notes/<int:note_id>", methods=["PUT"])
@token_required
def update_note(current_user, note_id):
    data = request.get_json()
    
    note = Note.query.get(note_id)
    if not note:
        return jsonify({"error": "Note not found"}), 404

    note.title = data.get("title", note.title)
    note.note = data.get("note", note.note)
    
    db.session.commit()

    return jsonify({"message": "Note updated successfully"})

# --- FILES APIs ---

@note_file_bp.route('/files', methods=['POST'])
@token_required
def upload_file(current_user):
    print("[DEBUG] Form Data:", request.form)
    
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "Empty filename"}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    file.save(filepath)

    # 🔥 ADD THIS BLOCK: Database Insert
    try:
        new_file = File(
            entity_type=request.form.get("entity_type"),
            entity_id=request.form.get("entity_id"),
            file_name=filename,
            file_path=filepath,
            file_size=os.path.getsize(filepath),
            file_type=file.content_type,
            uploaded_by=current_user.id,
            company_id=current_user.organization_id,
            created_at=datetime.utcnow()
        )

        db.session.add(new_file)
        db.session.commit()

        return jsonify({
            "message": "File uploaded successfully",
            "filename": filename,
            "file_id": new_file.id
        })
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] DB Insert Failed: {e}")
        return jsonify({"error": "Database error", "details": str(e)}), 500

@note_file_bp.route('/files', methods=['GET'])
@token_required
def get_files(current_user):
    entity_type = request.args.get("entity_type")
    entity_id = request.args.get("entity_id")

    # Start with a base query filtered by the user's organization for security
    query = File.query.filter_by(company_id=current_user.organization_id)

    if entity_type:
        query = query.filter_by(entity_type=entity_type)

    if entity_id:
        query = query.filter_by(entity_id=entity_id)

    files = query.all()

    result = []
    for f in files:
        result.append({
            "id": f.id,
            "file_name": f.file_name,
            "file_type": f.file_type,
            "file_size": f.file_size,
            "uploaded_by": f.uploaded_by,
            "company_id": f.company_id
        })

    return jsonify(result)

@note_file_bp.route('/files/<int:file_id>/download', methods=['GET'])
@token_required
def download_file_by_id(current_user, file_id):
    file_record = File.query.get(file_id)

    if not file_record:
        return jsonify({"error": "File not found"}), 404

    return send_file(file_record.file_path, as_attachment=True)

@note_file_bp.route('/files/<filename>', methods=['GET'])
def download_file(filename):
    return send_from_directory("uploads", filename)

@note_file_bp.route('/files/<int:file_id>', methods=['DELETE'])
@token_required
def delete_file(current_user, file_id):
    print("DELETE ID:", file_id)
    
    file_record = File.query.get(file_id)

    if not file_record:
        return jsonify({"error": "File not found"}), 404

    # delete file from folder
    if file_record.file_path and os.path.exists(file_record.file_path):
        os.remove(file_record.file_path)

    # delete from DB
    db.session.delete(file_record)
    db.session.commit()

    return jsonify({"message": "File deleted successfully"})

@note_file_bp.route('/files/<filename>', methods=['PUT'])
def update_file(filename):
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    if not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404

    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']

    # overwrite
    file.save(filepath)

    return jsonify({"message": "File updated successfully"})