from flask import Blueprint, request, jsonify
from extensions import db
from models.call import Call
import requests
import os

call_bp = Blueprint('call_bp', __name__)

@call_bp.route("/make-call", methods=["POST"])
def make_call():
    data = request.get_json()
    to_number = data.get("number")

    if not to_number:
        return jsonify({"error": "Phone number is required"}), 400

    sid = os.getenv('EXOTEL_SID')
    api_key = os.getenv('EXOTEL_API_KEY')
    api_token = os.getenv('EXOTEL_API_TOKEN')
    caller_id = os.getenv('EXOTEL_CALLER_ID')

    if not all([sid, api_key, api_token, caller_id]):
        return jsonify({"error": "Exotel configuration missing in .env"}), 500

    # Exotel API URL
    url = f"https://{api_key}:{api_token}@api.exotel.com/v1/Accounts/{sid}/Calls/connect.json"

    payload = {
        "From": caller_id,
        "To": to_number,
        "CallerId": caller_id
    }    

    try:
        response = requests.post(url, data=payload)
        response_data = response.json()
        
        # Save to DB
        call_sid = response_data.get("Call", {}).get("Sid")
        status = response_data.get("Call", {}).get("Status", "initiated")

        log = Call(
            customer_number=to_number,
            direction="outgoing",
            status=status,
            call_sid=call_sid
        )
        db.session.add(log)
        db.session.commit()

        return jsonify(response_data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@call_bp.route("/incoming-call", methods=["POST"])
def incoming_call():
    # Exotel sends data as form-data
    caller = request.form.get("From")
    call_sid = request.form.get("CallSid")
    status = request.form.get("CallStatus")
    
    if caller:
        log = Call(
            customer_number=caller,
            direction="incoming",
            status=status,
            call_sid=call_sid
        )
        db.session.add(log)
        db.session.commit()

    return "OK", 200

@call_bp.route("/call-logs", methods=["GET"])
def get_call_logs():
    logs = Call.query.order_by(Call.created_at.desc()).all()
    return jsonify([log.to_dict() for log in logs])