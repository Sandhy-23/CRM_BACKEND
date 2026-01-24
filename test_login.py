import requests
import json

BASE_URL = "http://127.0.0.1:5000"

def test_admin_login():
    url = f"{BASE_URL}/auth/login"
    payload = {
        "email": "sandhyarani23@gmail.com",
        "password": "sandhya23"
    }
    
    print(f"🔄 Attempting login for: {payload['email']}...")
    
    try:
        response = requests.post(url, json=payload)
        print(f"📊 Status Code: {response.status_code}")
        print("📄 Response Body:")
        print(json.dumps(response.json(), indent=4))
    except Exception as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    test_admin_login()