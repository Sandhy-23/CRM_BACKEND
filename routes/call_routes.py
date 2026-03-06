from flask import Blueprint, request, jsonify
from extensions import db
from models.call import Call
from models.crm import Lead
from models.contact import Contact
from models.user import User
import os
import requests
from routes.auth_routes import token_required
from datetime import datetime

call_bp = Blueprint('call_bp', __name__)

def format_number(num):
    """Formats number to E.164 format, e.g., +919876543210"""
    if not num:
        return None
    # Remove common characters except '+'
    num = str(num).strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    
    if num.startswith('+'):
        return num
        
    # If it's a 10-digit Indian number, add +91
    if len(num) == 10 and num.isdigit():
        return "+91" + num
        
    # If it's a 12-digit Indian number (91...), add +
    if len(num) == 12 and num.startswith('91') and num.isdigit():
        return "+" + num
        
    # Fallback: return the cleaned number, Twilio might handle it.
    return num

@call_bp.route("/call-lead/<int:lead_id>", methods=["POST"])
@token_required
def call_lead(current_user, lead_id):
    lead = Lead.query.get_or_404(lead_id)

    if not lead.phone:
        return jsonify({"error": "Lead has no phone number"}), 400

    customer_number = lead.phone

    try:
        sid = os.getenv("EXOTEL_SID")
        api_key = os.getenv("EXOTEL_API_KEY")
        api_token = os.getenv("EXOTEL_API_TOKEN")
        agent_number = os.getenv("EXOTEL_AGENT_NUMBER")
        caller_id = os.getenv("EXOTEL_CALLER_ID")

        # Debug print statements as requested
        print("--- Exotel Debug (call-lead) ---")
        print("EXOTEL SID:", sid)
        print("EXOTEL KEY:", api_key)
        print("EXOTEL TOKEN:", api_token)
        print("AGENT:", agent_number)
        print("CALLER ID:", caller_id)
        print("--------------------------------")

        if not all([sid, api_key, api_token, agent_number]):
            return jsonify({"error": "Exotel credentials are not fully configured on the server."}), 500

        url = f"https://api.exotel.com/v1/Accounts/{sid}/Calls/connect.json"

        formatted_customer_number = format_number(customer_number)

        payload = {
            "From": formatted_customer_number,
            "To": agent_number,
            "CallerId": caller_id
        }

        api_response = requests.post(url, data=payload, auth=(api_key, api_token))
        api_response.raise_for_status()
        response_data = api_response.json()

        call_details = response_data.get('Call', {})
        call_sid = call_details.get('Sid')

        # Log the outgoing call
        log = Call(
            agent_id=current_user.id,
            customer_number=formatted_customer_number,
            direction="outgoing",
            status=call_details.get('Status', 'initiated'),
            call_sid=call_sid
        )
        db.session.add(log)
        db.session.commit()

        return jsonify({"message": "Call initiated successfully to lead", "response": response_data}), 200

    except Exception as e:
        print(f"[FAIL] Exotel call failed for lead {lead_id}: {str(e)}")
        return jsonify({"error": "Failed to initiate call via Exotel", "details": str(e)}), 500

@call_bp.route("/incoming-call", methods=["POST"])
def incoming_call():
    # Exotel sends data as form-data (application/x-www-form-urlencoded)
    caller = request.form.get("From")
    call_sid = request.form.get("CallSid")
    status = request.form.get("CallStatus")
    agent_number = request.form.get("DialWhomNumber") # Agent's number from Exotel

    agent_id = None
    agent = None
    if agent_number:
        formatted_agent_number = format_number(agent_number)
        agent = User.query.filter((User.phone == formatted_agent_number) | (User.mobile_number == formatted_agent_number)).first()
        if agent:
            agent_id = agent.id
            print(f"✅ Incoming call mapped to agent: {agent.name} (ID: {agent_id})")
    
    if caller:
        formatted_caller = format_number(caller)
        lead = Lead.query.filter((Lead.phone == caller) | (Lead.phone == formatted_caller)).first()
        
        if not lead:
            org_id = agent.organization_id if agent else 1 # Assign to agent's org or default
            lead = Lead(
                name=f"Unknown Caller {formatted_caller}",
                phone=formatted_caller,
                source="Incoming Call",
                status="New",
                organization_id=org_id,
                assigned_user_id=agent_id # Auto-assign lead to agent
            )
            db.session.add(lead)
            db.session.commit()
            print(f"✅ Auto-created lead for incoming call: {formatted_caller}")

        log = Call(
            customer_number=formatted_caller,
            direction="incoming",
            status=status,
            call_sid=call_sid
        )
        db.session.add(log)
        db.session.commit()

    return "OK", 200