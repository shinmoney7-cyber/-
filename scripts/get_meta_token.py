"""
Meta (Instagram/Facebook) Long-lived Access Token 발급 (1회 실행)
필요: Meta Developer 앱 생성 후 App ID, App Secret 입력
"""
import os, webbrowser, requests
from urllib.parse import urlencode, urlparse, parse_qs
import http.server, threading

APP_ID = os.environ.get("META_APP_ID") or input("Meta App ID: ").strip()
APP_SECRET = os.environ.get("META_APP_SECRET") or input("Meta App Secret: ").strip()
REDIRECT_URI = "http://localhost:8080/callback"

SCOPE = "instagram_basic,instagram_content_publish,pages_read_engagement,pages_show_list,pages_manage_posts"

auth_url = "https://www.facebook.com/v20.0/dialog/oauth?" + urlencode({
    "client_id": APP_ID,
    "redirect_uri": REDIRECT_URI,
    "scope": SCOPE,
    "response_type": "code",
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

# Short-lived token
r1 = requests.get("https://graph.facebook.com/v20.0/oauth/access_token", params={
    "client_id": APP_ID, "client_secret": APP_SECRET,
    "redirect_uri": REDIRECT_URI, "code": code,
})
short_token = r1.json().get("access_token", "")

# Long-lived token (60일)
r2 = requests.get("https://graph.facebook.com/v20.0/oauth/access_token", params={
    "grant_type": "fb_exchange_token",
    "client_id": APP_ID, "client_secret": APP_SECRET,
    "fb_exchange_token": short_token,
})
long_token = r2.json().get("access_token", "")

# Instagram User ID 조회
r3 = requests.get("https://graph.facebook.com/v20.0/me/accounts", params={"access_token": long_token})
pages = r3.json().get("data", [])
for page in pages:
    page_id = page.get("id")
    page_token = page.get("access_token")
    # Instagram 연결 계정
    r4 = requests.get(f"https://graph.facebook.com/v20.0/{page_id}", params={
        "fields": "instagram_business_account",
        "access_token": page_token,
    })
    ig_id = r4.json().get("instagram_business_account", {}).get("id", "")
    print(f"\n페이지: {page.get('name')}")
    print(f"  FACEBOOK_PAGE_ID={page_id}")
    print(f"  FACEBOOK_PAGE_ACCESS_TOKEN={page_token}")
    if ig_id:
        print(f"  INSTAGRAM_USER_ID={ig_id}")
        print(f"  INSTAGRAM_ACCESS_TOKEN={long_token}")

print("\n✅ 위 값들을 GitHub Secrets에 저장하세요")
