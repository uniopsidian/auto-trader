import requests

REST_API_KEY = "3e477d72c6059110488cdf6d0dbce9e6"
CLIENT_SECRET = "vfjYErfQOQRYkzNmZ6AHs3EvYqt9G81N"
REDIRECT_URI = "http://localhost:4000/redirect"
AUTH_CODE = "812SV3kblG_-XQ4FCjXBK8ZySB5fPah554_E0_ARAatJbJ0RQZ5f3QAAAAQKDRXYAAABnZAezCyxu3fh8M0xkQ"

url = "https://kauth.kakao.com/oauth/token"

data = {
    "grant_type": "authorization_code",
    "client_id": REST_API_KEY,
    "client_secret": CLIENT_SECRET,
    "redirect_uri": REDIRECT_URI,
    "code": AUTH_CODE,
}

response = requests.post(url, data=data, timeout=15)

print("status_code:", response.status_code)
print("response_text:", response.text)