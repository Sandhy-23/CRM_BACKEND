from datetime import datetime
from extensions import db
from models.automation import (
    AutomationRule,
    AutomationCondition,
    AutomationAction,
    AutomationLog
)

# ===============================
# MAIN ENTRY POINT
# ===============================
def run_automation(trigger_type, lead, old_values=None):
    """
    trigger_type: lead_created | lead_updated | status_changed
    lead: SQLAlchemy Lead object
    old_values: dict (optional) - for status change detection
    """

    rules = (
        AutomationRule.query
        .filter_by(is_active=True, trigger_type=trigger_type)
        .order_by(AutomationRule.priority.asc())
        .all()
    )

    for rule in rules:
        # Prevent self-loop
        if rule_already_executed(rule.id, lead.id):
            continue

        # Trigger from -> to check (for status change)
        if trigger_type == "status_changed":
            if not old_values:
                continue

            if rule.trigger_from and old_values.get("status") != rule.trigger_from:
                continue

            if rule.trigger_to and lead.status != rule.trigger_to:
                continue

        # Match conditions
        if not match_conditions(rule, lead):
            continue

        # Execute actions
        try:
            execute_actions(rule, lead)
            log_rule_execution(rule, lead)

            if rule.stop_processing:
                break

        except Exception as e:
            db.session.rollback()
            print(f"[AUTOMATION ERROR] Rule {rule.id}: {str(e)}")

    db.session.commit()


# ===============================
# CONDITION MATCHER
# ===============================
def match_conditions(rule, lead):
    results = []

    for condition in rule.conditions:
        lead_value = getattr(lead, condition.field, None)
        condition_value = condition.value

        if lead_value is None:
            results.append(False)
            continue

        if condition.operator == "equals":
            results.append(str(lead_value) == condition_value)

        elif condition.operator == "contains":
            results.append(condition_value.lower() in str(lead_value).lower())

        elif condition.operator == "greater_than":
            results.append(float(lead_value) > float(condition_value))

        elif condition.operator == "less_than":
            results.append(float(lead_value) < float(condition_value))

        else:
            results.append(False)

    return (
        all(results)
        if rule.condition_logic == "AND"
        else any(results)
    )


# ===============================
# ACTION EXECUTOR
# ===============================
def execute_actions(rule, lead):
    for action in rule.actions:

        if action.action_type == "assign_user":
            lead.assigned_user_id = int(action.action_value)

        elif action.action_type == "assign_team":
            lead.assigned_team_id = int(action.action_value)

        elif action.action_type == "update_status":
            lead.status = action.action_value

        elif action.action_type == "archive":
            lead.is_archived = True

        elif action.action_type == "send_email":
            send_email(action.action_value, lead)

        elif action.action_type == "add_tag":
            add_tag_to_lead(lead, action.action_value)

        else:
            print(f"[UNKNOWN ACTION] {action.action_type}")

    db.session.add(lead)


# ===============================
# LOGGING
# ===============================
def log_rule_execution(rule, lead):
    log = AutomationLog(
        rule_id=rule.id,
        lead_id=lead.id,
        created_at=datetime.utcnow(),
        action_executed="RULE_EXECUTED"
    )
    db.session.add(log)


def rule_already_executed(rule_id, lead_id):
    return AutomationLog.query.filter_by(
        rule_id=rule_id,
        lead_id=lead_id
    ).first() is not None


# ===============================
# HELPERS (PLUG LATER)
# ===============================
def send_email(template_id, lead):
    print(f"Email sent using template {template_id} to {lead.email}")


def add_tag_to_lead(lead, tag):
    if not lead.tags:
        lead.tags = tag
    else:
        lead.tags += f",{tag}"