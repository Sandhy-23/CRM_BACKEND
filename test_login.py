import requests
import json

BASE_URL = "http://127.0.0.1:5000"

def test_login():
    url = f"{BASE_URL}/auth/login"
    # Credentials from your successful signup
    payload = {
        "email": "srani@gamil.com",
        "password": "srani23"
    }
    
    print(f"🔄 Attempting login for: {payload['email']}...")
    
    try:
        response = requests.post(url, json=payload)
        print(f"📊 Status Code: {response.status_code}")
        print("📄 Response Body:")
        print(json.dumps(response.json(), indent=4))
        
        if response.status_code == 200:
            token = response.json().get("token")
            print(f"\n✅ Login Successful! Token: {token[:20]}...")
        else:
            print(f"\n❌ Login Failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    test_login()