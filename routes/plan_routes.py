from flask import Blueprint, request, jsonify
from extensions import db
from models.plan import Plan, Feature
from models.organization import Organization
from routes.auth_routes import token_required

plan_bp = Blueprint("plans", __name__)

# --- Manage Plans & Features (Super Admin) ---

@plan_bp.route("/plans", methods=["POST"])
@token_required
def create_plan(current_user):
    if current_user.role not in ["Super Admin", "Admin"]:
        return jsonify({"message": "Unauthorized"}), 403
    
    data = request.get_json()
    if not data or not data.get("name"):
        return jsonify({"message": "Plan name is required"}), 400

    if Plan.query.filter_by(name=data.get("name")).first():
        return jsonify({"message": "Plan with this name already exists"}), 409

    new_plan = Plan(
        name=data.get("name"),
        price=data.get("price"),
        user_limit=data.get("user_limit"),
        description=data.get("description")
    )
    db.session.add(new_plan)
    db.session.commit()
    return jsonify({"message": "Plan created", "plan": new_plan.to_dict()}), 201

@plan_bp.route("/features", methods=["POST"])
@token_required
def create_feature(current_user):
    if current_user.role not in ["Super Admin", "Admin"]:
        return jsonify({"message": "Unauthorized"}), 403
    
    data = request.get_json()
    new_feature = Feature(name=data.get("name"), key=data.get("key"))
    db.session.add(new_feature)
    db.session.commit()
    return jsonify({"message": "Feature created"}), 201

@plan_bp.route("/plans/<int:plan_id>/features", methods=["POST"])
@token_required
def add_feature_to_plan(current_user, plan_id):
    if current_user.role not in ["Super Admin", "Admin"]:
        return jsonify({"message": "Unauthorized"}), 403

    data = request.get_json()
    feature_key = data.get("feature_key")
    
    plan = Plan.query.get(plan_id)
    feature = Feature.query.filter_by(key=feature_key).first()

    if plan and feature:
        if feature not in plan.features:
            plan.features.append(feature)
            db.session.commit()
        return jsonify({"message": "Feature added to plan"}), 200
    return jsonify({"message": "Plan or Feature not found"}), 404

# --- Manage Organizations (Super Admin) ---

@plan_bp.route("/organizations", methods=["POST"])
@token_required
def create_organization(current_user):
    if current_user.role not in ["Super Admin", "Admin"]:
        return jsonify({"message": "Unauthorized"}), 403
    
    data = request.get_json()
    name = data.get("name")
    
    if Organization.query.filter_by(name=name).first():
        return jsonify({"message": "Organization already exists"}), 400
        
    new_org = Organization(name=name)
    db.session.add(new_org)
    db.session.commit()
    
    return jsonify({"message": "Organization created", "organization": {"id": new_org.id, "name": new_org.name}}), 201

# --- Assign Plan to Company ---

@plan_bp.route("/organizations/<int:org_id>/assign-plan", methods=["PUT"])
@token_required
def assign_plan(current_user, org_id):
    if current_user.role not in ["Super Admin", "Admin"]:
        return jsonify({"message": "Unauthorized"}), 403

    data = request.get_json()
    plan_name = data.get("plan_name") # e.g., "Pro"
    
    org = Organization.query.get(org_id)
    plan = Plan.query.filter_by(name=plan_name).first()

    if not org or not plan:
        return jsonify({"message": "Organization or Plan not found"}), 404

    org.plan = plan
    org.subscription_plan = plan.name
    db.session.commit()

    return jsonify({"message": f"Assigned {plan.name} plan to {org.name}"}), 200

# --- Feature Access Control ---

@plan_bp.route("/check-access/<feature_key>", methods=["GET"])
@token_required
def check_feature_access(current_user, feature_key):
    """
    Dynamic check to see if the logged-in user's organization has access to a specific feature.
    """
    if not current_user.organization or not current_user.organization.plan:
        return jsonify({"has_access": False, "message": "No plan assigned"}), 403

    plan = current_user.organization.plan
    
    # Check if the feature exists in the plan's feature list
    has_access = any(f.key == feature_key for f in plan.features)
    
    if has_access:
        return jsonify({"has_access": True, "plan": plan.name}), 200
    else:
        return jsonify({"has_access": False, "message": f"Upgrade to access {feature_key}"}), 403

# --- Public List ---

@plan_bp.route("/plans", methods=["GET"])
def get_plans():
    plans = Plan.query.all()
    return jsonify([p.to_dict() for p in plans])