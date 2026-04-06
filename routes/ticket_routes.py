from flask import Blueprint, request, jsonify
from extensions import db
from routes.ticket import SupportTicket, TicketMessage, TicketNote, TicketActivity
from models.user import User
from models.organization import Organization
from routes.auth_routes import token_required, permission_required
from datetime import datetime, timedelta

ticket_bp = Blueprint('tickets', __name__)

# --- 🔹 STEP 2: HELPER FUNCTIONS ---

def calculate_sla(ticket):
    """Computes SLA status and time remaining dynamically."""
    now = datetime.utcnow()
    first_due = ticket.first_response_due_at
    resolution_due = ticket.resolution_due_at

    # Breach check
    first_breached = first_due and now > first_due and not ticket.first_responded_at
    resolution_breached = resolution_due and now > resolution_due and not ticket.resolved_at

    # SLA Status
    if first_breached or resolution_breached:
        sla_status = "Breached"
    else:
        sla_status = "On Track"

    # Time remaining calculation
    if ticket.resolved_at:
        time_remaining = "Met"
    elif first_breached:
        diff = now - first_due
        time_remaining = f"-{int(diff.total_seconds() // 3600)}h {int((diff.total_seconds() // 60) % 60)}m"
    else:
        diff = first_due - now
        time_remaining = f"{int(diff.total_seconds() // 3600)}h {int((diff.total_seconds() // 60) % 60)}m"

    return sla_status, time_remaining, first_breached, resolution_breached

# --- 🔹 STEP 3: CREATE TICKET ---

@ticket_bp.route("/", methods=["POST"])
@token_required
@permission_required("Tickets", "create")
def create_ticket(current_user):
    data = request.get_json()
    
    # Generate ID (TKT-001 format)
    last_ticket = SupportTicket.query.order_by(SupportTicket.id.desc()).first()
    new_id = f"TKT-{int(last_ticket.id.split('-')[1]) + 1:03}" if last_ticket else "TKT-001"

    now = datetime.utcnow()
    org = db.session.get(Organization, current_user.organization_id)

    ticket = SupportTicket(
        id=new_id,
        title=data["title"],
        description=data.get("description"),
        priority=data["priority"],
        category=data["category"],
        submitted_by=current_user.name,
        company=org.name if org else "Default",
        created_at=now,
        updated_at=now,
        first_response_due_at=now + timedelta(hours=2),
        resolution_due_at=now + timedelta(hours=24),
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
        sla_status, time_remaining, fb, rb = calculate_sla(t)
        result.append({
            "id": t.id,
            "title": t.title,
            "status": t.status,
            "priority": t.priority,
            "assignee": t.assignee,
            "submittedBy": t.submitted_by,
            "createdAt": t.created_at.isoformat(),
            "responses": t.responses,
            "slaStatus": sla_status,
            "timeRemaining": time_remaining
        })

    return jsonify({"tickets": result})

# --- 🔹 STEP 5: SEND MESSAGE ---

@ticket_bp.route("/<id>/messages", methods=["POST"])
@token_required
@permission_required("Tickets", "edit")
def send_message(current_user, id):
    data = request.get_json()
    ticket = SupportTicket.query.get_or_404(id)

    message = TicketMessage(
        ticket_id=id,
        type=data["type"],
        author=current_user.name,
        body=data["body"]
    )

    ticket.responses += 1
    ticket.updated_at = datetime.utcnow()

    # FIRST RESPONSE LOGIC
    if data["type"] == "agent" and not ticket.first_responded_at:
        ticket.first_responded_at = datetime.utcnow()

    db.session.add(message)
    db.session.commit()
    return jsonify({"message": "Sent"})

@ticket_bp.route("/<id>/messages", methods=["GET"])
@token_required
@permission_required("Tickets", "view")
def get_messages(current_user, id):
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
    data = request.get_json()
    ticket = SupportTicket.query.get_or_404(id)

    ticket.status = data["status"]
    ticket.updated_at = datetime.utcnow()

    if data["status"] in ["Resolved", "Closed"]:
        ticket.resolved_at = datetime.utcnow()

    db.session.commit()
    return jsonify({"message": "Updated"})

# --- 🔹 STEP 7: ASSIGN USER ---

@ticket_bp.route("/<id>/assign", methods=["PUT"])
@token_required
@permission_required("Tickets", "edit")
def assign_ticket(current_user, id):
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
    activities = TicketActivity.query.filter_by(ticket_id=id).order_by(TicketActivity.created_at.desc()).all()
    return jsonify([{
        "id": a.id,
        "action": a.action,
        "color": a.color,
        "createdAt": a.created_at.isoformat()
    } for a in activities])