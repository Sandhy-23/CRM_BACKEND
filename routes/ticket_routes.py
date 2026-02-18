from flask import Blueprint, request, jsonify
from extensions import db
from models.ticket import Ticket, TicketComment
from routes.auth_routes import token_required
from services.sla_service import calculate_sla_due
from datetime import datetime
import uuid

ticket_bp = Blueprint('tickets', __name__)

@ticket_bp.route('/', methods=['POST'])
@token_required
def create_ticket(current_user):
    data = request.get_json()
    
    if not data.get('subject'):
        return jsonify({'message': 'Subject is required'}), 400

    # Generate unique ticket number (e.g., TKT-A1B2C3)
    ticket_number = "TKT-" + str(uuid.uuid4().hex)[:6].upper()

    new_ticket = Ticket(
        ticket_number=ticket_number,
        subject=data.get('subject'),
        description=data.get('description'),
        priority=data.get('priority', 'Medium'),
        status='Open',
        category=data.get('category'),
        contact_id=data.get('contact_id'),
        assigned_to=data.get('assigned_to'),
        organization_id=current_user.organization_id,
        created_at=datetime.utcnow()
    )
    
    db.session.add(new_ticket)
    # We need to flush to get the ticket object with its properties (like priority)
    # before passing it to the SLA calculation service.
    db.session.flush()
    
    # SLA Calculation
    new_ticket.sla_due_at = calculate_sla_due(new_ticket)
    
    db.session.commit()

    return jsonify({'message': 'Ticket created successfully', 'ticket': {
        'id': new_ticket.id,
        'ticket_number': new_ticket.ticket_number,
        'sla_due_at': new_ticket.sla_due_at.isoformat() if new_ticket.sla_due_at else None
    }}), 201

@ticket_bp.route('/', methods=['GET'])
@token_required
def get_tickets(current_user):
    tickets = Ticket.query.filter_by(organization_id=current_user.organization_id).order_by(Ticket.created_at.desc()).all()
    
    result = []
    for t in tickets:
        result.append({
            "id": t.id,
            "ticket_number": t.ticket_number,
            "subject": t.subject,
            "priority": t.priority,
            "status": t.status,
            "category": t.category,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "assigned_to": t.assignee.name if t.assignee else None
        })
    
    return jsonify(result), 200

@ticket_bp.route('/<int:ticket_id>', methods=['PUT'])
@token_required
def update_ticket(current_user, ticket_id):
    ticket = Ticket.query.filter_by(id=ticket_id, organization_id=current_user.organization_id).first_or_404()
    data = request.get_json()

    if 'status' in data:
        ticket.status = data['status']
        if ticket.status == 'Closed' and not ticket.closed_at:
            ticket.closed_at = datetime.utcnow()
        elif ticket.status != 'Closed':
            ticket.closed_at = None
            
    if 'priority' in data: ticket.priority = data['priority']
    if 'assigned_to' in data: ticket.assigned_to = data['assigned_to']
    if 'category' in data: ticket.category = data['category']

    db.session.commit()
    return jsonify({'message': 'Ticket updated successfully'}), 200

@ticket_bp.route('/<int:ticket_id>/comment', methods=['POST'])
@token_required
def add_comment(current_user, ticket_id):
    ticket = Ticket.query.filter_by(id=ticket_id, organization_id=current_user.organization_id).first_or_404()
    data = request.get_json()
    
    if not data.get('comment'):
        return jsonify({'message': 'Comment is required'}), 400

    comment = TicketComment(
        ticket_id=ticket.id,
        user_id=current_user.id,
        comment=data['comment'],
        is_internal=data.get('is_internal', False),
        created_at=datetime.utcnow()
    )
    
    db.session.add(comment)
    db.session.commit()
    
    return jsonify({'message': 'Comment added successfully'}), 201

@ticket_bp.route("/sla/breached", methods=["GET"])
@token_required
def get_breached_tickets(current_user):
    """Returns tickets that have passed their SLA due time and are not closed."""
    now = datetime.utcnow()

    breached = Ticket.query.filter(
        Ticket.organization_id == current_user.organization_id,
        Ticket.sla_due_at != None,
        Ticket.sla_due_at < now,
        Ticket.status != "Closed"
    ).all()

    return jsonify([
        {
            "id": t.id,
            "ticket_number": t.ticket_number,
            "subject": t.subject,
            "priority": t.priority,
            "sla_due_at": t.sla_due_at.isoformat() if t.sla_due_at else None
        }
        for t in breached
    ]), 200