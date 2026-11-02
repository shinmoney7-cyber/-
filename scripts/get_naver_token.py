"""
네이버 OAuth Refresh Token 발급 (1회 실행)
https://developers.naver.com/docs/login/api/api.md
"""
import os, webbrowser, requests, secrets
from urllib.parse import urlencode, urlparse, parse_qs
import http.server, threading

CLIENT_ID = os.environ.get("NAVER_CLIENT_ID") or input("Naver Client ID: ").strip()
CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET") or input("Naver Client Secret: ").strip()
REDIRECT_URI = "http://localhost:8080/callback"
STATE = secrets.token_urlsafe(16)

auth_url = "https://nid.naver.com/oauth2.0/authorize?" + urlencode({
    "response_type": "code",
    "client_id": CLIENT_ID,
    "redirect_uri": REDIRECT_URI,
    "state": STATE,
})

code_holder = {}

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        qs = parse_qs(urlparse(self.path).query)
        code_holder["code"] = qs.get("code", [""])[0]
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"<h1>OK!</h1>")
    def log_message(self, *args): pass

server = http.server.HTTPServer(("", 8080), Handler)
t = threading.Thread(target=server.handle_request)
t.start()

print(f"\n브라우저에서 인증:\n{auth_url}\n")
try: webbrowser.open(auth_url)
except Exception: pass

t.join(timeout=120)
code = code_holder.get("code") or input("code: ").strip()

res = requests.get("https://nid.naver.com/oauth2.0/token", params={
    "grant_type": "authorization_code",
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "code": code,
    "state": STATE,
})
data = res.json()
refresh_token = data.get("refresh_token", "")

if refresh_token:
    print(f"\n✅ NAVER_REFRESH_TOKEN:\n{refresh_token}")
    print("\nGitHub Secrets에 저장:")
    print(f"  NAVER_CLIENT_ID={CLIENT_ID}")
    print(f"  NAVER_CLIENT_SECRET={CLIENT_SECRET}")
    print(f"  NAVER_REFRESH_TOKEN={refresh_token}")
else:
    print("❌ 실패:", data)
