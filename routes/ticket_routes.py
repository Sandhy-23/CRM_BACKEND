from flask import Blueprint, request, jsonify
from extensions import db
from routes.ticket import SupportTicket, TicketMessage, TicketNote, TicketActivity
from models.user import User
from models.organization import Organization
from routes.auth_routes import token_required, permission_required
from datetime import datetime, timedelta

ticket_bp = Blueprint('tickets', __name__) # Keep this line

# --- 🔹 STEP 3: CREATE TICKET ---

@ticket_bp.route("/", methods=["POST"])
@token_required
@permission_required("Tickets", "create")
def create_ticket(current_user):
    data = request.get_json()
    
    # Generate ID (TKT-001 format)
    last_ticket = SupportTicket.query.order_by(SupportTicket.id.desc()).first()
    new_id = f"TKT-{int(last_ticket.id.split('-')[1]) + 1:03}" if last_ticket else "TKT-001"

    ticket = SupportTicket(
        id=data.get("id") or new_id,
        title=data.get("title"),
        description=data.get("description"),
        category=data.get("category"),
        priority=data.get("priority"),
        status=data.get("status", "open"),
        sla_status=data.get("sla_status"),
        assignee=data.get("assignee"),
        submitted_by=data.get("submitted_by") or current_user.name,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        organization_id=current_user.organization_id
    )

    db.session.add(ticket)
    db.session.commit()
    return jsonify({"message": "Ticket created", "id": new_id}), 201

# --- 🔹 STEP 4: GET ALL TICKETS ---

@ticket_bp.route("/", methods=["GET"])
@token_required
@permission_required("Tickets", "view")
def get_tickets(current_user):
    tickets = SupportTicket.query.filter_by(organization_id=current_user.organization_id).all()
    result = []
    for t in tickets:
        result.append({ # Changed keys to match requested output
            "Ticket #": t.id,
            "Ticket": t.title,
            "Category": t.category,
            "Priority": t.priority,
            "Status": t.status,
            "SLA Status": t.sla_status,
            "Assignee": t.assignee,
            "Submitted By": t.submitted_by,
            "Last Updated": t.updated_at.isoformat() if isinstance(t.updated_at, datetime) else str(t.updated_at)
        })
    return jsonify(result)

# --- 🔹 STEP 5: SEND MESSAGE ---

@ticket_bp.route("/<id>/messages", methods=["POST"])
@token_required
@permission_required("Tickets", "edit")
def send_message(current_user, id):
    if not id or id == "undefined":
        return jsonify({"error": "Invalid ticket id"}), 400
    data = request.get_json()
    print("Incoming data:", data)

    # ✅ STEP 3: Validation (Don't skip)
    if not data or not (data.get("body") or data.get("message")):
        return jsonify({"error": "Message body is required"}), 400

    if not data.get("type"):
        return jsonify({"error": "Type is required"}), 400

    ticket = SupportTicket.query.get_or_404(id)

    # ✅ STEP 2 & 4: Safe access and full corrected logic
    message = TicketMessage(
        ticket_id=id,
        type=data.get("type"),
        author=current_user.name,
        body=data.get("body") or data.get("message")
    )
    ticket.updated_at = datetime.utcnow() # Keep updated_at

    db.session.add(message)
    db.session.commit()
    return jsonify({"message": "Sent"})

@ticket_bp.route("/<id>/messages", methods=["GET"])
@token_required
@permission_required("Tickets", "view")
def get_messages(current_user, id):
    if not id or id == "undefined":
        return jsonify({"error": "Invalid ticket id"}), 400
    messages = TicketMessage.query.filter_by(ticket_id=id).order_by(TicketMessage.created_at.asc()).all()
    return jsonify([{
        "id": m.id,
        "type": m.type,
        "author": m.author,
        "body": m.body,
        "createdAt": m.created_at.isoformat()
    } for m in messages])

# --- 🔹 STEP 6: UPDATE STATUS ---

@ticket_bp.route("/<id>/status", methods=["PUT"])
@token_required
@permission_required("Tickets", "edit")
def update_status(current_user, id):
    if not id or id == "undefined":
        return jsonify({"error": "Invalid ticket id"}), 400
    data = request.get_json()
    ticket = SupportTicket.query.get_or_404(id)

    ticket.status = data["status"]
    ticket.updated_at = datetime.utcnow() # Keep updated_at
    # Removed resolved_at logic as that field is removed from model

    db.session.commit()
    return jsonify({"message": "Updated"})

# --- 🔹 STEP 7: ASSIGN USER ---

@ticket_bp.route("/<id>/assign", methods=["PUT"])
@token_required
@permission_required("Tickets", "edit")
def assign_ticket(current_user, id):
    if not id or id == "undefined":
        return jsonify({"error": "Invalid ticket id"}), 400
    data = request.get_json()
    ticket = SupportTicket.query.get_or_404(id)

    ticket.assignee = data["assignee"]
    ticket.updated_at = datetime.utcnow()

    db.session.commit()
    return jsonify({"message": "Assigned"})

# --- 🔹 ADDITIONAL: NOTES & ACTIVITY ---

@ticket_bp.route("/<id>/notes", methods=["POST"])
@token_required
@permission_required("Tickets", "edit")
def add_note(current_user, id):
    if not id or id == "undefined":
        return jsonify({"error": "Invalid ticket id"}), 400
    data = request.get_json()
    note = TicketNote(
        ticket_id=id,
        author=current_user.name,
        body=data["body"]
    )
    db.session.add(note)
    db.session.commit()
    return jsonify({"message": "Note added"})

@ticket_bp.route("/<id>/activity", methods=["GET"])
@token_required
@permission_required("Tickets", "view")
def get_activity(current_user, id):
    if not id or id == "undefined":
        return jsonify({"error": "Invalid ticket id"}), 400
    activities = TicketActivity.query.filter_by(ticket_id=id).order_by(TicketActivity.created_at.desc()).all()
    return jsonify([{
        "id": a.id,
        "action": a.action,
        "color": a.color,
        "createdAt": a.created_at.isoformat()
    } for a in activities])