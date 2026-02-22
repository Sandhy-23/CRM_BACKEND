from flask import Blueprint, request, jsonify
from openai import OpenAI
from extensions import db
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from routes.auth_routes import token_required
import os

ai_chatbot_bp = Blueprint("ai_chatbot", __name__)

# Using the refined "Master Prompt" structure for clarity and security.
SYSTEM_PROMPT = """
You are a secure internal CRM assistant and an expert in generating SQL queries.

STRICT RULES:
- Generate ONLY valid SQL SELECT queries.
- Never generate DELETE, UPDATE, INSERT, DROP, ALTER, TRUNCATE.
- Never modify the database schema or data.
- Do not provide any explanations, introductions, or summaries.
- Use only the tables and columns provided below.
- If the user asks to modify data or for something outside of a SELECT query, respond exactly with: This assistant only provides information.
- Return ONLY the raw SQL query and nothing else.

Available Database Tables and Columns:
users(id, name, email, role, target)
leads(id, name, email, status, owner, created_at)
deals(id, title, value, status, owner, created_at)
activities(id, type, user_id, lead_id, deal_id, created_at)
"""

@ai_chatbot_bp.route("/api/ai-chat", methods=["POST"])
@token_required
def ai_chat(current_user): # Add current_user from decorator

    # Initialize client here to ensure env vars are loaded
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    user_message = request.json.get("message")
    if not user_message:
        return jsonify({"error": "The 'message' field is required."}), 400

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ]
    )

    sql_query = response.choices[0].message.content.strip()

    # --- MULTI-LAYER SECURITY VALIDATION ---

    # Layer 1: Block dangerous keywords
    dangerous_keywords = [
        "delete", "update", "insert",
        "drop", "alter", "truncate",
        "create", "replace"
    ]
    sql_lower = sql_query.lower()

    if any(word in sql_lower for word in dangerous_keywords):
        return jsonify({"reply": "Unsafe query blocked. This assistant only provides information."}), 403

    # Layer 2: Ensure it's a SELECT query
    if not sql_lower.startswith("select"):
        return jsonify({"reply": "Only SELECT queries are allowed. This assistant only provides information."}), 403

    # Layer 3: Prevent SQL statement injection by blocking multiple statements
    if ";" in sql_query.strip().rstrip(';'):
        return jsonify({"reply": "Multiple SQL statements are not allowed."}), 403

    try:
        result = db.session.execute(text(sql_query)).fetchall()
        data = [dict(row._mapping) for row in result]
        # Return the generated SQL for debugging/transparency, as suggested
        return jsonify({
            "generated_sql": sql_query,
            "data": data
        })

    except ProgrammingError as e:
        # This catches SQL syntax errors from the AI, which is a likely scenario.
        print(f"[FAIL] AI Chatbot SQL Error: {e.orig}")
        return jsonify({
            "message": "The generated query had a syntax error.",
            "generated_sql": sql_query,
            "error": "Invalid SQL syntax. Please try rephrasing your question."
        }), 400
    except Exception as e:
        # Catch-all for other potential issues (DB connection, etc.)
        print(f"[FAIL] AI Chatbot General Error: {str(e)}")
        return jsonify({
            "message": "An unexpected error occurred while executing the query.",
            "generated_sql": sql_query,
            "error": str(e)
        }), 500