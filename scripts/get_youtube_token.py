"""
YouTube OAuth2 Refresh Token 발급 (1회 실행)
실행: YOUTUBE_CLIENT_ID=xxx YOUTUBE_CLIENT_SECRET=yyy python scripts/get_youtube_token.py
"""
import os, json, webbrowser
from urllib.parse import urlencode, urlparse, parse_qs
import http.server, threading, requests

CLIENT_ID = os.environ.get("YOUTUBE_CLIENT_ID") or input("Client ID: ").strip()
CLIENT_SECRET = os.environ.get("YOUTUBE_CLIENT_SECRET") or input("Client Secret: ").strip()
REDIRECT_URI = "http://localhost:8080/callback"
SCOPE = "https://www.googleapis.com/auth/youtube.upload"

auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode({
    "client_id": CLIENT_ID,
    "redirect_uri": REDIRECT_URI,
    "response_type": "code",
    "scope": SCOPE,
    "access_type": "offline",
    "prompt": "consent",
})

code_holder = {}

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        qs = parse_qs(urlparse(self.path).query)
        code_holder["code"] = qs.get("code", [""])[0]
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"<h1>OK! 터미널로 돌아가세요.</h1>")
    def log_message(self, *args): pass

server = http.server.HTTPServer(("", 8080), Handler)
t = threading.Thread(target=server.handle_request)
t.start()

print(f"\n브라우저에서 인증하세요:\n{auth_url}\n")
try:
    webbrowser.open(auth_url)
except Exception:
    pass

t.join(timeout=120)
code = code_holder.get("code", "")
if not code:
    print("❌ 코드를 받지 못했습니다. URL에서 code= 값을 수동으로 입력하세요:")
    code = input("code: ").strip()

res = requests.post("https://oauth2.googleapis.com/token", data={
    "code": code,
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "redirect_uri": REDIRECT_URI,
    "grant_type": "authorization_code",
})
data = res.json()
refresh_token = data.get("refresh_token", "")

if refresh_token:
    print(f"\n✅ YOUTUBE_REFRESH_TOKEN:\n{refresh_token}")
    print("\nGitHub Secrets에 저장하세요:")
    print(f"  YOUTUBE_CLIENT_ID={CLIENT_ID}")
    print(f"  YOUTUBE_CLIENT_SECRET={CLIENT_SECRET}")
    print(f"  YOUTUBE_REFRESH_TOKEN={refresh_token}")
else:
    print("❌ 실패:", data)
