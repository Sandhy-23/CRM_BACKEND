from flask import Blueprint, request, jsonify
from models.message import Message
from extensions import db

message_bp = Blueprint("message_bp", __name__, url_prefix="/api/messages")

@message_bp.route("/<int:conversation_id>", methods=["GET"])
def get_messages(conversation_id):
    messages = Message.query.filter_by(conversation_id=conversation_id).all()
    return jsonify([{
        "id": m.id,
        "content": m.content,
        "sender": m.sender,
        "status": m.status
    } for m in messages])