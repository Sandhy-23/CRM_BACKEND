from flask import Blueprint, request, jsonify
from models.landing_page import LandingPage
from extensions import db
from routes.auth_routes import token_required

landing_page_bp = Blueprint("landing_page_bp", __name__)

def serialize_landing(lp):
    return {
        "id": lp.id,
        "name": lp.name,
        "slug": lp.slug,
        "campaign": lp.campaign,
        "status": lp.status,
        "leads": lp.leads,
        "conversion": lp.conversion,
        "headline": lp.headline,
        "description": lp.description,
        "formFields": lp.form_fields,
        "visitors": lp.visitors,
        "createdAt": lp.created_at.isoformat() if lp.created_at else None,
        "updatedAt": lp.updated_at.isoformat() if lp.updated_at else None
    }

# GET /landing-pages
@landing_page_bp.route("/api/landing-pages", methods=["GET"])
@token_required
def get_landing_pages(current_user):
    pages = LandingPage.query.filter_by(organization_id=current_user.organization_id).all()
    return jsonify([serialize_landing(p) for p in pages])

# Analytics Endpoint
@landing_page_bp.route("/api/landing-pages/<string:id>/analytics", methods=["GET"])
@token_required
def analytics(current_user, id):
    lp = LandingPage.query.filter_by(id=id, organization_id=current_user.organization_id).first_or_404()

    if lp.visitors == 0:
        conversion = "0%"
    else:
        percent = (lp.leads / lp.visitors) * 100
        conversion = f"{round(percent, 1)}%"

    return jsonify({
        "visitors": lp.visitors,
        "leads": lp.leads,
        "conversion": conversion
    })