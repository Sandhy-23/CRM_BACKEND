from flask import Blueprint, request, jsonify
from extensions import db
from models.chat_message import ChatMessage
from services.crm_assistant import process_message
from routes.auth_routes import token_required

chat_bp = Blueprint("chat_bp", __name__)

# SEND MESSAGE
@chat_bp.route("/message", methods=["POST"])
@token_required
def send_message(current_user):
    data = request.get_json()
    message = data.get("message")

    if not message:
        return jsonify({"error": "Message required"}), 400

    # Save user message
    user_msg = ChatMessage(
        user_id=current_user.id,
        sender="user",
        message=message
    )
    db.session.add(user_msg)

    # Process assistant reply
    reply_text = process_message(message)

    # Save bot reply
    bot_msg = ChatMessage(
        user_id=current_user.id,
        sender="bot",
        message=reply_text
    )
    db.session.add(bot_msg)

    db.session.commit()

    return jsonify({
        "reply": reply_text
    })

# GET CHAT HISTORY
@chat_bp.route("/history", methods=["GET"])
@token_required
def get_history(current_user):
    messages = ChatMessage.query.filter_by(user_id=current_user.id).order_by(ChatMessage.created_at.asc()).all()

    result = []
    for msg in messages:
        result.append({
            "sender": msg.sender,
            "message": msg.message,
            "created_at": msg.created_at.isoformat()
        })

    return jsonify(result)