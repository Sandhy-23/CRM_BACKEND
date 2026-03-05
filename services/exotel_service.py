import requests
import os

def make_exotel_call(phone_number):

    sid = os.getenv("EXOTEL_SID")
    api_key = os.getenv("EXOTEL_KEY")
    api_token = os.getenv("EXOTEL_TOKEN")
    agent_number = os.getenv("AGENT_NUMBER")

    url = f"https://api.exotel.com/v1/Accounts/{sid}/Calls/connect.json"

    payload = {
        "From": agent_number,
        "To": f"+91{phone_number}",
        "CallerId": agent_number
    }

    response = requests.post(
        url,
        auth=(api_key, api_token),
        data=payload
    )

    return response.json()