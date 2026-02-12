from flask import Blueprint, request, jsonify
from models.landing_page import LandingPage, LandingPageForm, FormSubmission, LandingPageEvent
from extensions import db
from datetime import datetime

landing_page_bp = Blueprint("landing_page_bp", __name__)


# Create Landing Page
@landing_page_bp.route("/api/landing-pages", methods=["POST"])
def create_landing_page():
    data = request.json

    page = LandingPage(
        name=data.get("name"),
        slug=data.get("slug"),
        branch_id=data.get("branch_id"),
        campaign_id=data.get("campaign_id"),
        organization_id=data.get("organization_id"),
        is_published=False
    )

    db.session.add(page)
    db.session.commit()

    return jsonify({"message": "Landing page created", "id": page.id}), 201


# Get All Landing Pages
@landing_page_bp.route("/api/landing-pages", methods=["GET"])
def get_landing_pages():
    pages = LandingPage.query.all()

    result = []
    for page in pages:
        result.append({
            "id": page.id,
            "name": page.name,
            "slug": page.slug,
            "is_published": page.is_published
        })

    return jsonify(result)


# Form Submit
@landing_page_bp.route("/api/form-submit", methods=["POST"])
def form_submit():
    data = request.json

    submission = FormSubmission(
        form_id=data.get("form_id"),
        data=data.get("data"),
        ip_address=request.remote_addr
    )

    db.session.add(submission)
    db.session.commit()

    return jsonify({"message": "Form submitted successfully"}), 201