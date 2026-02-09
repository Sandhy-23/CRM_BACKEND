from flask import Blueprint, request, jsonify
from extensions import db
from models.conversation import Conversation
from models.message import Message
from models.crm import Lead
from models.channel_account import ChannelAccount
from services.automation_engine import run_workflow
from datetime import datetime

webhook_bp = Blueprint('webhooks', __name__)

@webhook_bp.route('/api/webhooks/whatsapp', methods=['POST', 'GET'])
def whatsapp_webhook():
    # Verification
    if request.method == 'GET':
        return request.args.get('hub.challenge', 'OK'), 200

    data = request.get_json()
    
    try:
        entry = data.get('entry', [])[0]
        changes = entry.get('changes', [])[0]
        value = changes.get('value', {})
        
        if 'messages' in value:
            msg_data = value['messages'][0]
            sender_phone = msg_data.get('from')
            content = msg_data.get('text', {}).get('body', '')
            
            # 1. Find Lead
            lead = Lead.query.filter_by(phone=sender_phone).first()
            
            if not lead:
                # Create Lead
                # Find org from channel account (simplified)
                # In prod, map phone_number_id to ChannelAccount
                lead = Lead(
                    name=f"WhatsApp {sender_phone}",
                    phone=sender_phone,
                    source='whatsapp',
                    status='new',
                    organization_id=1 # Default or dynamic
                )
                db.session.add(lead)
                db.session.commit()
                
            # 2. Find Conversation
            conversation = Conversation.query.filter_by(
                lead_id=lead.id, 
                channel='whatsapp'
            ).first()
            
            if not conversation:
                conversation = Conversation(
                    channel='whatsapp',
                    lead_id=lead.id,
                    organization_id=lead.organization_id,
                    status='open'
                )
                db.session.add(conversation)
                db.session.commit()
                
            # 3. Insert Message
            message = Message(
                conversation_id=conversation.id,
                channel='whatsapp',
                sender_type='customer',
                content=content,
                status='received'
            )
            db.session.add(message)
            
            conversation.last_message_at = datetime.utcnow()
            db.session.commit()
            
            # 4. Run Automation
            run_workflow(
                trigger="new_message",
                deal=lead # Passing lead as 'deal' context for now, or update engine
            )
            
            # 5. Emit Socket Event (if configured)
            try:
                from app import socketio
                socketio.emit('new_message', message.to_dict(), room=str(conversation.organization_id))
            except:
                pass
                
            return jsonify({'status': 'processed'}), 200
            
    except Exception as e:
        print(f"Webhook Error: {e}")
        return jsonify({'status': 'error'}), 500
    
    return jsonify({'status': 'ignored'}), 200