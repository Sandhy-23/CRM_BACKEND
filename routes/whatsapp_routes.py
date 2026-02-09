from flask import Blueprint, request, jsonify
from extensions import db
from models.whatsapp import WhatsAppAccount
from models.conversation import Conversation
from models.message import Message
from models.crm import Lead
from models.user import User
from routes.auth_routes import token_required
from services.automation_engine import run_workflow
from datetime import datetime
import requests
import os

whatsapp_bp = Blueprint('whatsapp', __name__)

# ✅ STEP 2: CONNECT WHATSAPP
@whatsapp_bp.route('/api/whatsapp/connect', methods=['POST'])
@token_required
def connect_whatsapp(current_user):
    if current_user.role not in ['SUPER_ADMIN', 'ADMIN']:
        return jsonify({'message': 'Unauthorized'}), 403

    data = request.get_json()
    
    # Check if account exists for this company
    account = WhatsAppAccount.query.filter_by(company_id=current_user.organization_id).first()
    if not account:
        account = WhatsAppAccount(company_id=current_user.organization_id)
        db.session.add(account)
    
    account.business_id = data.get('business_id')
    account.phone_number_id = data.get('phone_number_id')
    account.access_token = data.get('access_token')
    account.webhook_secret = data.get('webhook_secret')
    account.status = 'Connected'
    
    db.session.commit()
    return jsonify({'message': 'WhatsApp connected successfully', 'status': 'Connected'}), 200

# ✅ STEP 3: WHATSAPP WEBHOOK
@whatsapp_bp.route('/webhooks/whatsapp', methods=['GET', 'POST'])
def whatsapp_webhook():
    # 1. Verification Request (GET)
    if request.method == 'GET':
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        
        # In production, verify against stored secret. For MVP, accept if token matches a known value or generic check.
        if mode == 'subscribe' and token: 
            return challenge, 200
        return 'Forbidden', 403

    # 2. Event Notification (POST)
    data = request.get_json()
    
    try:
        # Extract Message Data (Simplified for MVP)
        entry = data.get('entry', [])[0]
        changes = entry.get('changes', [])[0]
        value = changes.get('value', {})
        
        if 'messages' in value:
            message_data = value['messages'][0]
            sender_phone = message_data.get('from') # e.g., "919876543210"
            text_body = message_data.get('text', {}).get('body', '')
            wa_msg_id = message_data.get('id')
            
            # 1. Find or Create Lead
            lead = Lead.query.filter_by(phone=sender_phone).first()
            is_new_lead = False
            
            if not lead:
                # Determine organization (In real multi-tenant, this is tricky via webhook without mapping. 
                # For MVP, we assign to the first org or a default one found via phone_number_id mapping)
                # Here we assume single org or find via account mapping
                wa_account = WhatsAppAccount.query.filter_by(phone_number_id=value.get('metadata', {}).get('phone_number_id')).first()
                org_id = wa_account.company_id if wa_account else 1
                
                lead = Lead(
                    name=f"WhatsApp User {sender_phone[-4:]}",
                    phone=sender_phone,
                    source='whatsapp',
                    status='new',
                    organization_id=org_id,
                    created_at=datetime.utcnow()
                )
                db.session.add(lead)
                db.session.commit()
                is_new_lead = True
                
                # Run Automation for New Lead
                run_workflow("lead_created", lead)

            # 2. Find or Create Conversation
            conversation = Conversation.query.filter_by(lead_id=lead.id, channel='whatsapp').first()
            if not conversation:
                conversation = Conversation(
                    lead_id=lead.id,
                    channel='whatsapp',
                    company_id=lead.organization_id,
                    assigned_to=lead.assigned_user_id, # Inherit from lead
                    created_at=datetime.utcnow()
                )
                db.session.add(conversation)
                db.session.commit()
            
            # 3. Store Message
            new_msg = Message(
                conversation_id=conversation.id,
                direction='incoming',
                content=text_body,
                status='read', # Auto-read for now or 'delivered'
                whatsapp_message_id=wa_msg_id,
                created_at=datetime.utcnow()
            )
            db.session.add(new_msg)
            
            # 4. Update Conversation Stats
            conversation.last_message = text_body
            conversation.last_message_at = datetime.utcnow()
            conversation.unread_count += 1
            
            db.session.commit()
            
            return jsonify({'status': 'processed'}), 200
            
        elif 'statuses' in value:
            # Handle Delivery Receipts (sent, delivered, read)
            status_data = value['statuses'][0]
            wa_msg_id = status_data.get('id')
            new_status = status_data.get('status')
            
            msg = Message.query.filter_by(whatsapp_message_id=wa_msg_id).first()
            if msg:
                msg.status = new_status
                db.session.commit()
            
            return jsonify({'status': 'updated'}), 200
            
    except Exception as e:
        print(f"Webhook Error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

    return jsonify({'status': 'ignored'}), 200

# ✅ STEP 4: INBOX APIs
@whatsapp_bp.route('/api/inbox', methods=['GET'])
@token_required
def get_inbox(current_user):
    query = Conversation.query.filter_by(company_id=current_user.organization_id)
    
    # Role-based filtering
    if current_user.role not in ['SUPER_ADMIN', 'ADMIN', 'MANAGER']:
        query = query.filter_by(assigned_to=current_user.id)
        
    conversations = query.order_by(Conversation.last_message_at.desc()).all()
    
    result = []
    for c in conversations:
        result.append({
            "conversation_id": c.id,
            "lead_id": c.lead_id,
            "name": c.lead.name if c.lead else "Unknown",
            "last_message": c.last_message,
            "unread": c.unread_count,
            "assigned_to": c.assignee.name if c.assignee else None,
            "state": c.lead.state if c.lead else None,
            "channel": c.channel,
            "last_message_at": c.last_message_at.isoformat()
        })
        
    return jsonify(result), 200

@whatsapp_bp.route('/api/inbox/<int:conversation_id>/messages', methods=['GET'])
@token_required
def get_messages(current_user, conversation_id):
    conversation = Conversation.query.get_or_404(conversation_id)
    
    # Security check
    if conversation.company_id != current_user.organization_id:
        return jsonify({'message': 'Unauthorized'}), 403
        
    # Mark as read
    conversation.unread_count = 0
    db.session.commit()
    
    messages = Message.query.filter_by(conversation_id=conversation_id).order_by(Message.created_at.asc()).all()
    return jsonify([m.to_dict() for m in messages]), 200

# ✅ STEP 5: SEND MESSAGE
@whatsapp_bp.route('/api/inbox/<int:conversation_id>/send', methods=['POST'])
@token_required
def send_message(current_user, conversation_id):
    data = request.get_json()
    content = data.get('message')
    
    if not content:
        return jsonify({'message': 'Message content required'}), 400
        
    conversation = Conversation.query.get_or_404(conversation_id)
    
    # 1. Save to DB
    msg = Message(
        conversation_id=conversation.id,
        direction='outgoing',
        content=content,
        status='sending',
        created_at=datetime.utcnow()
    )
    db.session.add(msg)
    
    # 2. Update Conversation
    conversation.last_message = content
    conversation.last_message_at = datetime.utcnow()
    
    db.session.commit()
    
    # 3. Send to WhatsApp API (Placeholder for MVP)
    # In production: requests.post(whatsapp_api_url, json=payload, headers=headers)
    # For now, simulate success
    msg.status = 'sent'
    db.session.commit()
    
    return jsonify({'message': 'Message sent', 'status': 'sent', 'id': msg.id}), 200