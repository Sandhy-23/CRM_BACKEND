from flask import Blueprint, request, jsonify
import pymysql
from datetime import datetime

web_conversion_bp = Blueprint('web_conversion', __name__)

def get_db():
    """
    Establishes a database connection using pymysql.
    Note: This uses direct pymysql, separate from SQLAlchemy ORM used elsewhere.
    """
    return pymysql.connect(
        host="localhost",
        user="root",
        password="1234", # Updated to match application settings
        database="crm_db",
        cursorclass=pymysql.cursors.DictCursor
    )

def check_auth():
    """
    Basic authentication check for the provided APIs.
    Verifies the presence of an Authorization header.
    """
    token = request.headers.get('Authorization')
    if not token:
        return False
    # In a real application, you would validate the token (e.g., JWT) here.
    return True

@web_conversion_bp.route('/api/web-conversions', methods=['GET'])
def get_conversions():
    if not check_auth():
        return jsonify({"error": "Unauthorized"}), 401

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM web_conversions ORDER BY created_at DESC")
    data = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(data)

@web_conversion_bp.route('/api/web-conversions', methods=['POST'])
def create_conversion():
    if not check_auth():
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json

    conn = get_db()
    cursor = conn.cursor()

    query = """
    INSERT INTO web_conversions 
    (first_name, last_name, email, phone, company, conversion_type, source, page, message)
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """

    cursor.execute(query, (
        data.get('first_name'),
        data.get('last_name'),
        data.get('email'),
        data.get('phone'),
        data.get('company'),
        data.get('conversion_type'),
        data.get('source'),
        data.get('page'),
        data.get('message')
    ))

    conn.commit()

    new_id = cursor.lastrowid

    cursor.execute("SELECT * FROM web_conversions WHERE id=%s", (new_id,))
    new_data = cursor.fetchone()

    cursor.close()
    conn.close()

    return jsonify(new_data), 201

@web_conversion_bp.route('/api/web-conversions/<int:id>/status', methods=['PUT'])
def update_status(id):
    if not check_auth():
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE web_conversions SET status=%s WHERE id=%s",
        (data.get('status'), id)
    )

    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({"message": "Status updated"})

@web_conversion_bp.route('/api/conversion/stats', methods=['GET'])
def get_stats():
    if not check_auth():
        return jsonify({"error": "Unauthorized"}), 401

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as leads FROM web_conversions")
    leads = cursor.fetchone()['leads']

    visitors = 5200 # Fake visitors as per prompt
    conversion_rate = round((leads / visitors) * 100, 2) if visitors else 0

    cursor.close()
    conn.close()

    return jsonify({
        "visitors": visitors, "visitorTrend": "+12% vs last month",
        "leads": leads, "leadTrend": "+5% vs last week",
        "conversion": conversion_rate, "conversionTrend": "Stable"
    })

@web_conversion_bp.route('/api/conversion/trends', methods=['GET'])
def get_trends():
    if not check_auth():
        return jsonify({"error": "Unauthorized"}), 401

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            DATE(created_at) as day,
            COUNT(*) as leads
        FROM web_conversions
        GROUP BY DATE(created_at)
        ORDER BY day ASC
    """)

    rows = cursor.fetchall()

    result = []
    for r in rows:
        # r['day'] is a datetime.date object, so strftime works
        result.append({
            "day": r['day'].strftime('%a'),
            "visitors": 300,  # fake for now
            "leads": r['leads']
        })

    cursor.close()
    conn.close()

    return jsonify(result)