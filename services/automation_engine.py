from datetime import datetime
from extensions import db
from models.automation import Automation, AutomationRule, AutomationAction, WorkflowLog
from models.note_file import Note

print("automation_engine loaded")

# ===============================
# MAIN ENTRY POINT
# ===============================
def run_workflow(trigger, deal):
    """
    trigger: "deal_created" | "deal_updated"
    deal: Deal object
    """
    print(f"[WORKFLOW] Trigger: {trigger}")
    print(f"[WORKFLOW] Deal ID: {deal.id}")
    
    automations = Automation.query.filter_by(
        trigger_event=trigger,
        is_active=True,
        company_id=deal.organization_id
    ).all()

    for auto in automations:
        if rules_match(auto.id, deal):
            print(f"[AUTOMATION] Rules matched for Automation ID: {auto.id}. Executing actions...")
            execute_actions(auto.id, deal)
            save_log(auto.id, deal.id)

def rules_match(automation_id, deal):
    rules = AutomationRule.query.filter_by(
        automation_id=automation_id
    ).all()

    for rule in rules:
        # Get value from deal object dynamically
        deal_value = getattr(deal, rule.field, None)
        
        # Simple equality check (can be extended for other operators)
        if str(deal_value) != str(rule.value):
            return False
    return True

def execute_actions(automation_id, deal):
    actions = AutomationAction.query.filter_by(
        automation_id=automation_id
    ).all()

    for action in actions:
        if action.action_type == "update_stage":
            deal.stage = action.action_value
            db.session.commit()
            print(f"[ACTION] Updated Deal {deal.id} stage to {action.action_value}")
            
        elif action.action_type == "add_note":
            final_note = f"[Automation] {action.action_value} (Deal: {deal.title})"
            new_note = Note(note=final_note)
            db.session.add(new_note)
            db.session.commit()
            print(f"[ACTION] Added note: {final_note}")

def save_log(automation_id, deal_id):
    log = WorkflowLog(
        automation_id=automation_id,
        deal_id=deal_id,
        status="success"
    )
    db.session.add(log)
    db.session.commit()