from flask import Blueprint, request, jsonify
from extensions import db
from models.automation import Automation, AutomationCondition, AutomationAction
from routes.auth_routes import token_required
import json
import traceback

automation_bp = Blueprint('automation', __name__)

# --- Health Check (Requested) ---
@automation_bp.route("/api/automation/health", methods=["GET"])
def automation_health():
    return jsonify({"status": "automation module working"})

# --- Test Endpoint ---
@automation_bp.route("/automation/test", methods=["GET"])
def automation_test():
    return {"message": "Automation module working"}, 200

# --- Automations CRUD ---
def create_automation(current_user): # Now a helper function
    if current_user.role not in ['SUPER_ADMIN', 'ADMIN']:
        return jsonify({'message': 'Unauthorized'}), 403
        
    try:
        data = request.get_json()
        print(f"[DEBUG] /api/automation/rules Body: {data}")

        new_automation = Automation(
            name=data["name"],
            trigger_event=data["trigger_event"],
            branch_id=data["branch_id"],
            organization_id=current_user.organization_id,
            created_by=current_user.id,
            status=data.get("status", "active")
        )

        db.session.add(new_automation)
        db.session.flush() # Get ID
        
        # Conditions
        for cond in data.get("conditions", []):
            db.session.add(
                AutomationCondition(
                    automation_id=new_automation.id,
                    field=cond["field"],
                    operator=cond["operator"],
                    value=cond["value"]
                )
            )
            
        # Actions
        for act in data.get("actions", []):
            # Handle frontend sending 'action_type' or 'type'
            act_type = act.get("type") or act.get("action_type")
            
            db.session.add(
                AutomationAction(
                    automation_id=new_automation.id,
                    type=act_type,
                    template_id=act.get("template_id"),
                    delay_minutes=act.get("delay_minutes", 0)
                )
            )
            
        db.session.commit()
        return jsonify({'message': 'Automation created', 'automation': new_automation.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        print("❌ ERROR CREATING AUTOMATION:", str(e))
        traceback.print_exc()
        # Return 400 for validation/logic errors
        return jsonify({"success": False, "message": "Failed"}), 400

def get_automations(current_user): # Now a helper function
    automations = Automation.query.filter_by(
        organization_id=current_user.organization_id
    ).all()
    
    return jsonify([a.to_dict() for a in automations]), 200

@automation_bp.route('/automation/rules/<int:rule_id>/toggle', methods=['PUT'])
@token_required
def toggle_rule(current_user, rule_id):
    if current_user.role not in ['SUPER_ADMIN', 'ADMIN']:
        return jsonify({'message': 'Unauthorized'}), 403
        
    # Note: rule_id here refers to the Automation ID in the new structure
    automation = Automation.query.filter_by(id=rule_id, organization_id=current_user.organization_id).first()
    if not automation:
        return jsonify({'message': 'Automation not found'}), 404
        
    automation.status = 'paused' if automation.status == 'active' else 'active'
    db.session.commit()
    
    return jsonify({'message': f'Automation {automation.status}', 'status': automation.status}), 200

@automation_bp.route('/automation/rules', methods=['GET', 'POST'])
@token_required
def automation_rules(current_user):
    """
    Alias endpoint for /automations to match frontend expectations.
    """
    if request.method == 'POST':
        return create_automation(current_user)
    return get_automations(current_user)