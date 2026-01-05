from flask import Flask, jsonify
from extensions import db
from sqlalchemy.exc import IntegrityError
from routes import auth_bp, website_bp, dashboard_bp, plan_bp, quick_actions_bp, contact_bp
from routes.chart_routes import chart_bp
from config import Config
import models

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

app.register_blueprint(auth_bp, url_prefix="/auth")
app.register_blueprint(website_bp) # No prefix for main website
app.register_blueprint(dashboard_bp, url_prefix="/api")
app.register_blueprint(plan_bp, url_prefix="/api")
app.register_blueprint(chart_bp, url_prefix="/api")
app.register_blueprint(quick_actions_bp, url_prefix="/api")
app.register_blueprint(contact_bp)

@app.errorhandler(IntegrityError)
def handle_integrity_error(e):
    db.session.rollback()
    return jsonify({"error": "Database integrity error", "message": str(e.orig)}), 400

@app.errorhandler(405)
def handle_method_not_allowed(e):
    return jsonify({"error": "Method not allowed", "message": "The method is not allowed for the requested URL."}), 405

with app.app_context():
    # db.drop_all() # Uncomment this ONLY if you need to reset the DB completely
    db.create_all()
    
    # --- Seeding Script ---
    if not models.Plan.query.first():
        print("Seeding database with default plans and features...")
        
        # Create Features
        feat_user = models.Feature(name="User Management", key="user_management")
        feat_logs = models.Feature(name="Activity Logs", key="activity_logs")
        feat_analytics = models.Feature(name="Analytics", key="analytics")
        
        db.session.add_all([feat_user, feat_logs, feat_analytics])
        db.session.commit()
        
        # Create Plans & Link Features
        basic = models.Plan(name="Basic", price="$10/mo", user_limit=5, description="Entry level plan")
        basic.features.append(feat_user)
        
        pro_exec = models.Plan(name="Pro-Executive", price="$50/mo", user_limit=20, description="For growing teams")
        pro_exec.features.extend([feat_user, feat_logs])
        
        executive = models.Plan(name="Executive", price="$100/mo", user_limit=None, description="Full enterprise access")
        executive.features.extend([feat_user, feat_logs, feat_analytics])
        
        db.session.add_all([basic, pro_exec, executive])
        db.session.commit()
        print("Seeding complete.")

if __name__ == "__main__":
    app.run(debug=True)
