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

# Import existing role-based query helpers
from routes.contact_routes import get_contact_query
from routes.lead_routes import get_lead_query, Account
from routes.deal_routes import get_deal_query
from models.activity_logger import log_activity

import_export_bp = Blueprint('import_export', __name__)

# --- IMPORT LOGIC ---

def process_contact_import(df, current_user):
    """Handles the logic for importing contacts."""
    required_columns = ['first_name', 'email', 'mobile']
    if not all(col in df.columns for col in required_columns):
        missing = [col for col in required_columns if col not in df.columns]
        return jsonify({'error': 'File Processing Error', 'message': f'Missing required columns: {", ".join(missing)}'}), 400

    imported_count, failed_count, errors = 0, 0, []
    # Fetch existing emails and mobiles for duplicate checking
    existing_contacts = Contact.query.filter_by(organization_id=current_user.organization_id).with_entities(Contact.email, Contact.mobile).all()
    existing_emails = {c.email for c in existing_contacts}
    existing_mobiles = {c.mobile for c in existing_contacts if c.mobile}

    for index, row in df.iterrows():
        row_num = index + 2  # Account for header and 0-based index
        email = str(row.get('email', '')).strip()
        mobile = str(row.get('mobile', '')).strip()
        first_name = str(row.get('first_name', '')).strip()

        if not first_name:
            errors.append({'row': row_num, 'reason': 'Missing first_name'})
            failed_count += 1
            continue
        if not email or not mobile:
            errors.append({'row': row_num, 'reason': 'Missing email or mobile'})
            failed_count += 1
            continue
        if email in existing_emails:
            errors.append({'row': row_num, 'reason': f'Email "{email}" already exists in your organization'})
            failed_count += 1
            continue
        if mobile in existing_mobiles:
            errors.append({'row': row_num, 'reason': f'Mobile "{mobile}" already exists in your organization'})
            failed_count += 1
            continue

        try:
            new_contact = Contact(
                first_name=first_name,
                last_name=str(row.get('last_name', '')).strip(),
                name=f"{first_name} {str(row.get('last_name', '')).strip()}".strip(),
                email=email,
                mobile=mobile,
                phone=str(row.get('phone', '')).strip(),
                company=str(row.get('company', '')).strip(),
                status=str(row.get('status', 'Active')).strip(),
                source='Import',
                organization_id=current_user.organization_id,
                created_by=current_user.id,
                owner_id=current_user.id,
                assigned_to=current_user.id
            )
            db.session.add(new_contact)
            existing_emails.add(email)
            existing_mobiles.add(mobile)
            imported_count += 1
        except Exception as e:
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
    required_columns = ['last_name', 'company']
    if not all(col in df.columns for col in required_columns):
        missing = [col for col in required_columns if col not in df.columns]
        return jsonify({'error': 'File Processing Error', 'message': f'Missing required columns: {", ".join(missing)}'}), 400

    imported_count, failed_count, errors = 0, 0, []
    existing_emails = {l.email for l in Lead.query.filter_by(company_id=current_user.organization_id).filter(Lead.email.isnot(None)).all()}

    for index, row in df.iterrows():
        row_num = index + 2
        email = str(row.get('email', '')).strip()
        last_name = str(row.get('last_name', '')).strip()
        company = str(row.get('company', '')).strip()

        if not last_name:
            errors.append({'row': row_num, 'reason': 'Missing last_name'})
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
            new_lead = Lead(
                first_name=str(row.get('first_name', '')).strip(),
                last_name=last_name,
                company=company,
                email=email if email else None,
                phone=str(row.get('phone', '')).strip(),
                source='Import',
                status=str(row.get('status', 'New')).strip(),
                owner_id=current_user.id,
                company_id=current_user.organization_id
            )
            db.session.add(new_lead)
            if email: existing_emails.add(email)
            imported_count += 1
        except Exception as e:
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
        records = get_contact_query(current_user).filter(Contact.status == 'Active').all()
        if records: df = pd.DataFrame([r.to_dict() for r in records])
    
    elif module == 'leads':
        records = get_lead_query(current_user).filter(Lead.status != 'Converted').all()
        if records:
            data = [{
                "id": l.id, "first_name": l.first_name, "last_name": l.last_name,
                "company": l.company, "email": l.email, "phone": l.phone,
                "status": l.status, "source": l.source, "owner_id": l.owner_id,
                "created_at": l.created_at.isoformat() if l.created_at else None
            } for l in records]
            df = pd.DataFrame(data)

    elif module == 'deals':
        records = get_deal_query(current_user).all()
        if records:
            data = [{
                "id": d.id, "title": d.title, "amount": d.amount,
                "stage": d.stage, "owner_id": d.owner_id, "organization_id": d.organization_id,
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
        query = Note.query.filter_by(company_id=current_user.organization_id)
        if current_user.role not in ['SUPER_ADMIN', 'ADMIN', 'HR']:
            # For other roles, only export notes they created
            query = query.filter_by(created_by=current_user.id)
        records = query.all()
        if records: df = pd.DataFrame([r.to_dict() for r in records])

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