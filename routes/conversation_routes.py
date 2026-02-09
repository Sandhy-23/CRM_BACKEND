from flask import Blueprint, jsonify
from models.conversation import Conversation

conversation_bp = Blueprint("conversation_bp", __name__, url_prefix="/api/conversations")

@conversation_bp.route("/", methods=["GET"])
def get_conversations():
    conversations = Conversation.query.all()
    return jsonify([{
        "id": c.id,
        "channel": c.channel,
        "assigned_to": c.assigned_to,
        "status": c.status
    } for c in conversations])