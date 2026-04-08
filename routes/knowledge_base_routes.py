from flask import Blueprint, request, jsonify
from extensions import db
from sqlalchemy import text
from routes.auth_routes import token_required
from datetime import datetime

knowledge_bp = Blueprint('knowledge_base', __name__)

# ✔ 1. Get All Articles
@knowledge_bp.route('/', methods=['GET'])
@token_required
def get_articles(current_user):
    org_id = current_user.organization_id
    with db.engine.connect() as conn:
        query = text("""
            SELECT id, title, content, category, created_at 
            FROM knowledge_articles 
            WHERE organization_id = :org_id 
            ORDER BY created_at DESC
        """)
        result = conn.execute(query, {"org_id": org_id}).fetchall()
        # Convert row objects to dictionaries for JSON response
        articles = []
        for row in result:
            row_dict = dict(row._mapping)
            if row_dict.get('created_at'):
                row_dict['created_at'] = row_dict['created_at'].isoformat()
            articles.append(row_dict)
            
    return jsonify(articles), 200

# ✔ 2. Get Single Article
@knowledge_bp.route('/<int:id>', methods=['GET'])
@token_required
def get_article(current_user, id):
    org_id = current_user.organization_id
    with db.engine.connect() as conn:
        query = text("""
            SELECT id, title, content, category, created_at 
            FROM knowledge_articles 
            WHERE id = :id AND organization_id = :org_id
        """)
        result = conn.execute(query, {"id": id, "org_id": org_id}).fetchone()
        
        if not result:
            return jsonify({"error": "Article not found"}), 404
            
        article = dict(result._mapping)
        if article.get('created_at'):
            article['created_at'] = article['created_at'].isoformat()
            
    return jsonify(article), 200

# ✔ 3. Create Article
@knowledge_bp.route('/', methods=['POST'])
@token_required
def create_article(current_user):
    data = request.get_json()
    org_id = current_user.organization_id
    
    if not data or not data.get('title') or not data.get('content'):
        return jsonify({"error": "Title and content are required"}), 400

    with db.engine.begin() as conn:
        query = text("""
            INSERT INTO knowledge_articles (title, content, category, organization_id, created_at)
            VALUES (:title, :content, :category, :org_id, :created_at)
        """)
        conn.execute(query, {
            "title": data['title'],
            "content": data['content'],
            "category": data.get('category', 'General'),
            "org_id": org_id,
            "created_at": datetime.utcnow()
        })
        
    return jsonify({"message": "Article created"}), 201

# ✔ 4. Update Article
@knowledge_bp.route('/<int:id>', methods=['PUT'])
@token_required
def update_article(current_user, id):
    data = request.get_json()
    org_id = current_user.organization_id
    
    with db.engine.begin() as conn:
        query = text("""
            UPDATE knowledge_articles
            SET title = :title, content = :content, category = :category
            WHERE id = :id AND organization_id = :org_id
        """)
        result = conn.execute(query, {
            "title": data.get('title'),
            "content": data.get('content'),
            "category": data.get('category'),
            "id": id,
            "org_id": org_id
        })
        
        if result.rowcount == 0:
            return jsonify({"error": "Article not found or unauthorized"}), 404
        
    return jsonify({"message": "Updated"}), 200

# ✔ 5. Delete Article
@knowledge_bp.route('/<int:id>', methods=['DELETE'])
@token_required
def delete_article(current_user, id):
    org_id = current_user.organization_id
    with db.engine.begin() as conn:
        result = conn.execute(text("DELETE FROM knowledge_articles WHERE id = :id AND organization_id = :org_id"), 
                              {"id": id, "org_id": org_id})
        if result.rowcount == 0:
            return jsonify({"error": "Article not found"}), 404
            
    return jsonify({"message": "Deleted"}), 200