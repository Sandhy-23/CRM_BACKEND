from flask import Blueprint, request, jsonify
from extensions import db
from models.conversation import Conversation
from models.message import Message
from routes.auth_routes import token_required
from datetime import datetime

inbox_bp = Blueprint('inbox', __name__)

# 1. Get inbox list
@inbox_bp.route('/api/inbox', methods=['GET'])
@token_required
def get_inbox(current_user):
    query = Conversation.query.filter_by(organization_id=current_user.organization_id)
    
    # Permissions
    if current_user.role == 'SUPER_ADMIN':
        pass # See all
    elif current_user.role == 'MANAGER':
        # Filter by team (assuming user has team_id and lead has assigned_team_id)
        # For MVP, managers see all in org or we join with Lead to check team
        pass 
    else: # Agent
        query = query.filter_by(assigned_to=current_user.id)
        
    conversations = query.order_by(Conversation.last_message_at.desc()).all()
    
    result = []
    for c in conversations:
        # Join last message logic (simplified by using last_message_at sort)
        # Ideally we fetch the actual message content if needed
        last_msg = Message.query.filter_by(conversation_id=c.id).order_by(Message.created_at.desc()).first()
        
        result.append({
            "id": c.id,
            "lead_id": c.lead_id,
            "lead_name": c.lead.name if c.lead else "Unknown",
            "channel": c.channel,
            "status": c.status,
            "assigned_to": c.assigned_to,
            "last_message": last_msg.content if last_msg else "",
            "last_message_at": c.last_message_at.isoformat() if c.last_message_at else None,
            "unread_count": 0 # Implement logic if needed
        })
        
    return jsonify(result), 200

# 2. Get conversation messages
@inbox_bp.route('/api/inbox/<string:conversation_id>/messages', methods=['GET'])
@token_required
def get_messages(current_user, conversation_id):
    messages = Message.query.filter_by(conversation_id=conversation_id).order_by(Message.created_at.asc()).all()
    return jsonify([m.to_dict() for m in messages]), 200

# 3. Send message (agent -> customer)
@inbox_bp.route('/api/inbox/<string:conversation_id>/send', methods=['POST'])
@token_required
def send_message(current_user, conversation_id):
    data = request.get_json()
    content = data.get('message')
    
    if not content:
        return jsonify({'message': 'Content required'}), 400
        
    conversation = Conversation.query.get_or_404(conversation_id)
    
    # Save message
    msg = Message(
        conversation_id=conversation.id,
        channel=conversation.channel,
        sender_type='agent',
        content=content,
        status='sent'
    )
    db.session.add(msg)
    
    conversation.last_message_at = datetime.utcnow()
    db.session.commit()
    
    # TODO: Call WhatsApp/Email API here
    # emit('new_message', msg.to_dict(), room=conversation_id)
    
    return jsonify(msg.to_dict()), 201