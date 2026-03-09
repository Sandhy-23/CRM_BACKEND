from flask import Blueprint, request, jsonify
from extensions import db
from models.ticket import Ticket, TicketComment
from models.user import User
from routes.auth_routes import token_required
from datetime import datetime

ticket_bp = Blueprint('tickets', __name__)

# 1. Create Ticket
@ticket_bp.route('/', methods=['POST'])
@token_required
def create_ticket(current_user):
    data = request.get_json()
    
    new_ticket = Ticket(
        subject=data.get('subject'),
        description=data.get('description'),
        priority=data.get('priority', 'Medium'),
        category=data.get('category', 'General'),
        contact_id=current_user.id, # Created by current user
        organization_id=current_user.organization_id,
        status='Open'
    )
    
    db.session.add(new_ticket)
    db.session.flush() # Get ID to generate ticket number
    
    # Generate Ticket Number (e.g., TKT-1001)
    new_ticket.ticket_number = f"TCK-{new_ticket.id + 1000}"
    db.session.commit()
    
    return jsonify({"message": "Ticket created successfully", "ticket": new_ticket.to_dict()}), 201

# 2. Get Tickets (Role Based Visibility)
@ticket_bp.route('/', methods=['GET'])
@token_required
def get_tickets(current_user):
    query = Ticket.query.filter_by(organization_id=current_user.organization_id)
    
    role = current_user.role.upper() if current_user.role else ""
    
    # Case 1: Super Admin / Admin / Manager -> See All
    if role in ['SUPER_ADMIN', 'ADMIN', 'MANAGER']:
        pass 
    # Case 2: Employee -> See Assigned Only
    elif role == 'EMPLOYEE':
        query = query.filter_by(assigned_to=current_user.id)
    # Case 3: User / Contact -> See Created Only
    else:
        query = query.filter_by(contact_id=current_user.id)
        
    tickets = query.order_by(Ticket.created_at.desc()).all()

    # Map to frontend-specific keys as requested
    tickets_data = []
    for t in tickets:
        tickets_data.append({
            "id": t.id, # Keep ID for frontend keying
            "Ticket #": t.ticket_number,
            "Ticket": t.subject,
            "Category": t.category,
            "Priority": t.priority,
            "Status": t.status,
            "SLA Status": t.sla_due_at.strftime('%Y-%m-%d %H:%M:%S') if t.sla_due_at else "Not Set",
            "Assignee": t.assignee.name if t.assignee else "Unassigned",
            "Submitted By": t.creator.name if t.creator else "Unknown",
            "Last Updated": t.updated_at.strftime('%Y-%m-%d %H:%M:%S') if t.updated_at else None
        })
    return jsonify(tickets_data), 200

# 3. Assign Ticket
@ticket_bp.route('/<int:ticket_id>/assign', methods=['PUT'])
@token_required
def assign_ticket(current_user, ticket_id):
    # Only Admin/Manager can assign
    if current_user.role not in ['SUPER_ADMIN', 'ADMIN', 'MANAGER']:
        return jsonify({"error": "Unauthorized"}), 403
        
    ticket = Ticket.query.filter_by(id=ticket_id, organization_id=current_user.organization_id).first_or_404()
    data = request.get_json()
    
    employee_id = data.get('assigned_to')
    if not employee_id:
        return jsonify({"error": "Employee ID required"}), 400
        
    ticket.assigned_to = employee_id
    ticket.status = 'In Progress' # Auto update status on assignment
    db.session.commit()
    
    return jsonify({"message": "Ticket assigned successfully"}), 200

# 4. Update Ticket Status
@ticket_bp.route('/<int:ticket_id>', methods=['PUT'])
@token_required
def update_ticket(current_user, ticket_id):
    ticket = Ticket.query.filter_by(id=ticket_id, organization_id=current_user.organization_id).first_or_404()
    data = request.get_json()
    
    # Update fields if provided
    if 'status' in data:
        ticket.status = data['status']
        if data['status'] in ['Resolved', 'Closed']:
            ticket.closed_at = datetime.utcnow()
            
    if 'priority' in data:
        ticket.priority = data['priority']
        
    db.session.commit()
    return jsonify({"message": "Ticket updated", "ticket": ticket.to_dict()}), 200

# 5. Get Employees for Dropdown
@ticket_bp.route('/employees', methods=['GET'])
@token_required
def get_employees_for_assignment(current_user):
    if current_user.role not in ['SUPER_ADMIN', 'ADMIN', 'MANAGER']:
        return jsonify({"error": "Unauthorized"}), 403
        
    # Fetch users with role 'Employee', 'Manager', or 'Admin' in the org
    employees = User.query.filter(
        User.organization_id == current_user.organization_id,
        User.role.in_(['EMPLOYEE', 'ADMIN', 'MANAGER']),
        User.is_deleted == False
    ).all()
    
    return jsonify([{
        "id": u.id,
        "name": u.name,
        "email": u.email,
        "role": u.role
    } for u in employees]), 200