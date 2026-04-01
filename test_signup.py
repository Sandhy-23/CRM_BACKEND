import requests
import json

def test_signup():
    url = "http://127.0.0.1:5000/auth/signup"
    headers = {"Content-Type": "application/json"}
    
    # Payload for new user
    data = {
        "name": "Test User",
        "email": "test_user@example.com",
        "password": "password123"
    }

    print(f"🚀 Sending POST request to {url}...")
    try:
        response = requests.post(url, json=data, headers=headers)
        print(f"✅ Status Code: {response.status_code}")
        print(f"📄 Response: {response.text}")
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Is the Flask server running on port 5000?")

if __name__ == "__main__":
    test_signup()