from flask import Blueprint, request, jsonify
from extensions import db
from models.landing_page import LandingPage

landing_page_bp = Blueprint('landing_pages', __name__)

# 1. GET all landing pages
@landing_page_bp.route('/api/landing-pages', methods=['GET', 'OPTIONS'])
def get_landing_pages():
    if request.method == 'OPTIONS':
        return '', 200

    pages = LandingPage.query.order_by(LandingPage.created_at.desc()).all()

    result = []
    for p in pages:
        result.append({
            "id": p.id,
            "name": p.name,
            "slug": p.slug,
            "campaign": p.campaign,
            "status": p.status,
            "leads": p.leads,
            "conversion": p.conversion,
            "visitors": p.visitors,
            "created_at": p.created_at.isoformat() if p.created_at else None
        })

    return jsonify(result), 200

# 2. CREATE landing page
@landing_page_bp.route('/api/landing-pages', methods=['POST', 'OPTIONS'])
def create_landing_page():
    if request.method == 'OPTIONS':
        return '', 200

    data = request.get_json()
    
    if not data.get('name') or not data.get('slug'):
        return jsonify({"error": "Name and Slug are required"}), 400

    page = LandingPage(
        name=data.get('name'),
        slug=data.get('slug'),
        campaign=data.get('campaign'),
        status=data.get('status', 'Draft'),
        leads=0,
        conversion="0%",
        visitors=0,
        # Default organization_id to 1 if not provided (or handle via auth)
        organization_id=data.get('organization_id', 1) 
    )

    db.session.add(page)
    db.session.commit()

    return jsonify({"message": "Landing page created", "id": page.id}), 201

# 3. UPDATE landing page
@landing_page_bp.route('/api/landing-pages/<string:id>', methods=['PUT', 'OPTIONS'])
def update_landing_page(id):
    if request.method == 'OPTIONS':
        return '', 200

    page = LandingPage.query.get(id)

    if not page:
        return jsonify({"error": "Not found"}), 404

    data = request.get_json()

    if 'name' in data: page.name = data['name']
    if 'slug' in data: page.slug = data['slug']
    if 'status' in data: page.status = data['status']
    if 'campaign' in data: page.campaign = data['campaign']

    db.session.commit()

    return jsonify({"message": "Updated", "id": page.id}), 200

# 4. DELETE landing page
@landing_page_bp.route('/api/landing-pages/<string:id>', methods=['DELETE', 'OPTIONS'])
def delete_landing_page(id):
    if request.method == 'OPTIONS':
        return '', 200

    page = LandingPage.query.get(id)
    if not page:
        return jsonify({"error": "Not found"}), 404

    db.session.delete(page)
    db.session.commit()

    return jsonify({"message": "Deleted"}), 200