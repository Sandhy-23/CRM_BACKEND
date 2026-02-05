import pandas as pd
import io
from flask import Blueprint, request, jsonify, send_file
from extensions import db
from routes.auth_routes import token_required

# Import Models
from models.contact import Contact
from models.crm import Lead, Deal
from models.note_file import Note
from models.user import User
from datetime import datetime

# Import existing role-based query helpers
# The following imports are removed because 'get_lead_query' and 'Account' are no longer in lead_routes.py
# from routes.lead_routes import get_lead_query, Account
from routes.deal_routes import get_deal_query # Assuming this is still valid
from models.activity_logger import log_activity

import_export_bp = Blueprint('import_export', __name__)

# --- Helper: Account Model (Local Definition to fix import error) ---
class Account(db.Model):
    __tablename__ = 'accounts'
    id = db.Column(db.Integer, primary_key=True)
    account_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    website = db.Column(db.String(100))
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# --- IMPORT LOGIC ---

def process_contact_import(df, current_user):
    """Handles the logic for importing contacts."""
    required_columns = ['name', 'email']
    if not all(col in df.columns for col in required_columns):
        missing = [col for col in required_columns if col not in df.columns]
        return jsonify({'error': 'File Processing Error', 'message': f'Missing required columns: {", ".join(missing)}'}), 400

    imported_count, failed_count, errors = 0, 0, []
    # Fetch existing emails and mobiles for duplicate checking
    existing_emails = {c.email for c in Contact.query.with_entities(Contact.email).all()}

    for index, row in df.iterrows():
        row_num = index + 2  # Account for header and 0-based index
        email = str(row.get('email', '')).strip()
        name = str(row.get('name', '')).strip()

        if not name or not email:
            errors.append({'row': row_num, 'reason': 'Missing name or email'})
            failed_count += 1
            continue
        if email in existing_emails:
            errors.append({'row': row_num, 'reason': f'Email "{email}" already exists'})
            failed_count += 1
            continue

        try:
            new_contact = Contact(
                name=name,
                email=email,
                phone=str(row.get('phone', '')).strip(),
                company=str(row.get('company', '')).strip(),
                owner=str(row.get('owner', '')).strip(),
                last_contact=str(row.get('last_contact', '')).strip(),
                status=str(row.get('status', 'Active')).strip(),
            )
            db.session.add(new_contact)
            existing_emails.add(email)
            imported_count += 1
        except Exception as e:
            db.session.rollback()
            errors.append({'row': row_num, 'reason': f'Database error: {str(e)}'})
            failed_count += 1

    db.session.commit()
    log_activity(
        module="import",
        action="contacts_imported",
        description=f"Imported {imported_count} contacts. {failed_count} rows failed."
    )
    return jsonify({
        "total_rows": len(df), "imported": imported_count, "failed": failed_count, "errors": errors
    }), 200

def process_lead_import(df, current_user):
    """Handles the logic for importing leads."""
    required_columns = ['name', 'company']
    if not all(col in df.columns for col in required_columns):
        missing = [col for col in required_columns if col not in df.columns]
        return jsonify({'error': 'File Processing Error', 'message': f'Missing required columns: {", ".join(missing)}'}), 400

    imported_count, failed_count, errors = 0, 0, []
    existing_emails = {l.email for l in Lead.query.filter(Lead.email.isnot(None)).all()}

    for index, row in df.iterrows():
        row_num = index + 2
        email = str(row.get('email', '')).strip()
        name = str(row.get('name', '')).strip()
        company = str(row.get('company', '')).strip()

        if not name:
            errors.append({'row': row_num, 'reason': 'Missing name'})
            failed_count += 1
            continue
        if not company:
            errors.append({'row': row_num, 'reason': 'Missing company'})
            failed_count += 1
            continue
        if email and email in existing_emails:
            errors.append({'row': row_num, 'reason': f'Email "{email}" already exists for a lead in your organization'})
            failed_count += 1
            continue

        try:
            # Updated to match the new Lead model.
            # Fields like score, sla, owner, description are removed.
            # The system now auto-assigns users and teams upon API creation, but not for imports.
            new_lead = Lead(
                name=name,
                company=company,
                email=email if email else None,
                phone=str(row.get('phone', '')).strip(),
                source=str(row.get('source', 'Import')).strip(),
                status=str(row.get('status', 'new')).strip(), # Default status is 'new'
                # Location fields can be provided in the import file
                city=str(row.get('city', '')).strip() or None,
                state=str(row.get('state', '')).strip() or None,
                country=str(row.get('country', '')).strip() or None
            )
            db.session.add(new_lead)
            if email: existing_emails.add(email)
            imported_count += 1
        except Exception as e:
            db.session.rollback()
            errors.append({'row': row_num, 'reason': f'Database error: {str(e)}'})
            failed_count += 1
            
    db.session.commit()
    log_activity(
        module="import",
        action="leads_imported",
        description=f"Imported {imported_count} leads. {failed_count} rows failed."
    )
    return jsonify({
        "total_rows": len(df), "imported": imported_count, "failed": failed_count, "errors": errors
    }), 200

@import_export_bp.route('/import/<string:module>', methods=['POST'])
@token_required
def import_data(current_user, module):
    if 'file' not in request.files:
        return jsonify({'error': 'Validation Error', 'message': 'No file part in request'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Validation Error', 'message': 'No file selected'}), 400

    filename = file.filename.lower()
    if not (filename.endswith('.csv') or filename.endswith('.xlsx')):
        return jsonify({'error': 'Validation Error', 'message': 'Invalid file type. Please use CSV or XLSX.'}), 400

    try:
        df = pd.read_csv(file) if filename.endswith('.csv') else pd.read_excel(file)
        df.columns = [col.lower().replace(' ', '_').strip() for col in df.columns]
    except Exception as e:
        return jsonify({'error': 'File Read Error', 'message': str(e)}), 400

    if module == 'contacts':
        return process_contact_import(df, current_user)
    elif module == 'leads':
        return process_lead_import(df, current_user)
    else:
        return jsonify({'error': 'Not Found', 'message': f'Import for module "{module}" is not supported.'}), 404

# --- EXPORT LOGIC ---

@import_export_bp.route('/export/<string:module>', methods=['GET'])
@token_required
def export_data(current_user, module):
    df = pd.DataFrame()

    if module == 'contacts':
        records = Contact.query.all()
        if records:
            data = [{
                "id": r.id,
                "name": r.name,
                "company": r.company,
                "email": r.email,
                "phone": r.phone,
                "owner": r.owner,
                "last_contact": r.last_contact,
                "status": r.status
            } for r in records]
            df = pd.DataFrame(data)
    
    elif module == 'leads':
        # Replaced get_lead_query with a simple query.
        query = Lead.query
        # Simple RBAC for export: agents see their own leads, admins see all.
        if current_user.role not in ['SUPER_ADMIN', 'admin']:
             query = query.filter_by(assigned_user_id=current_user.id)

        records = query.filter(Lead.status != 'Converted').all()
        if records:
            # Updated data dictionary to match the new Lead model schema
            data = [{
                "id": l.id, "name": l.name,
                "company": l.company, "email": l.email, "phone": l.phone,
                "status": l.status, "source": l.source,
                "city": l.city,
                "state": l.state,
                "country": l.country,
                "assigned_team_id": l.assigned_team_id,
                "assigned_user_id": l.assigned_user_id,
                "created_at": l.created_at.isoformat() if l.created_at else None
            } for l in records]
            df = pd.DataFrame(data)

    elif module == 'deals':
        records = get_deal_query(current_user).all()
        if records:
            data = [{
                "id": d.id,
                "pipeline": d.pipeline,
                "title": d.title,
                "company": getattr(d, 'company', None),
                "stage": d.stage,
                "value": getattr(d, 'value', None),
                "owner": getattr(d, 'owner', None),
                "close_date": str(d.close_date) if d.close_date else None,
                "created_at": d.created_at.isoformat() if d.created_at else None
            } for d in records]
            df = pd.DataFrame(data)

    elif module == 'accounts':
        query = Account.query
        if current_user.role != 'SUPER_ADMIN':
            query = query.filter_by(organization_id=current_user.organization_id)
        records = query.all()
        if records:
            data = [{
                "id": a.id, "account_name": a.account_name, "phone": a.phone,
                "website": a.website, "owner_id": a.owner_id,
                "created_at": a.created_at.isoformat() if a.created_at else None
            } for a in records]
            df = pd.DataFrame(data)

    elif module == 'notes':
        # Export all notes (Simple Schema: id, note, created_at)
        query = Note.query.order_by(Note.created_at.desc())
        records = query.all()
        if records: 
            # Manual dict creation since to_dict might be outdated in model
            data = [{"id": r.id, "note": r.note, "created_at": r.created_at} for r in records]
            df = pd.DataFrame(data)

    else:
        return jsonify({'error': 'Not Found', 'message': f'Export for module "{module}" is not supported.'}), 404

    if df.empty:
        return jsonify({'message': 'No data available to export for your role.'}), 200

    # Create file in memory
    output = io.BytesIO()
    df.to_csv(output, index=False, encoding='utf-8')
    output.seek(0)

    return send_file(
        output,
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'{module}_export_{pd.Timestamp.now().strftime("%Y-%m-%d")}.csv'
    )