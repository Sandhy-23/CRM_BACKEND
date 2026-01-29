import json
from extensions import db
from models.automation_rule import AutomationRule
from models.task import Task 
from datetime import datetime, timedelta

def check_conditions(conditions_json, record):
    """Evaluates if the record matches the rule's conditions."""
    if not conditions_json:
        return True
    
    try:
        # Handle both string (from DB) and dict (if passed directly)
        if isinstance(conditions_json, str):
            conditions = json.loads(conditions_json)
        else:
            conditions = conditions_json
            
        # Logic: { "field": "source", "operator": "equals", "value": "Website" }
        field = conditions.get("field")
        operator = conditions.get("operator")
        value = conditions.get("value")
        
        if not field: return True # No valid condition found, assume match
        
        # Get the actual value from the record (e.g., lead.source)
        record_value = getattr(record, field, None)
        
        if operator == "equals":
            return str(record_value) == str(value)
        
        # Future: Add 'contains', 'greater_than', etc.
        
        return False
    except Exception as e:
        print(f"❌ Error checking conditions: {e}")
        return False

def execute_actions(actions_json, record, module, company_id, user_id):
    """Executes the defined actions if conditions are met."""
    if not actions_json:
        return

    try:
        if isinstance(actions_json, str):
            actions = json.loads(actions_json)
        else:
            actions = actions_json
            
        for action in actions:
            action_type = action.get("type")
            
            if action_type == "assign_owner":
                new_owner_id = action.get("user_id")
                # Update owner fields if they exist
                if hasattr(record, "owner_id"):
                    record.owner_id = new_owner_id
                if hasattr(record, "assigned_to"):
                    record.assigned_to = new_owner_id
                db.session.add(record)
                print(f"   -> Action: Assigned owner to User ID {new_owner_id}")
                
            elif action_type == "create_task":
                # Example: { "type": "create_task", "title": "Follow up", "days_due": 2 }
                days_due = action.get("days_due", 1)
                due_date = datetime.utcnow().date() + timedelta(days=days_due)
                
                new_task = Task(
                    title=action.get("title", f"Automated Task: {module}"),
                    description=f"Auto-generated for {module} ID: {record.id}",
                    status="Pending",
                    priority="Medium",
                    assigned_to=getattr(record, 'owner_id', user_id),
                    created_by=user_id, # System or trigger user
                    company_id=company_id,
                    due_date=due_date
                )
                
                # Link to record
                if module == 'lead': new_task.lead_id = record.id
                elif module == 'deal': new_task.deal_id = record.id
                    
                db.session.add(new_task)
                print(f"   -> Action: Created Task '{new_task.title}'")
                
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error executing automation actions: {e}")

def run_automation_rules(module, trigger_event, record, company_id, user_id):
    """Main entry point to trigger automation rules."""
    print(f"⚙️ Automation Engine: Checking rules for {module} ({trigger_event})...")
    
    rules = AutomationRule.query.filter_by(
        module=module,
        trigger_event=trigger_event,
        is_active=True,
        company_id=company_id
    ).all()
    
    for rule in rules:
        if check_conditions(rule.conditions, record):
            print(f"   ✅ Rule Matched: {rule.name}")
            execute_actions(rule.actions, record, module, company_id, user_id)