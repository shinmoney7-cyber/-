"""
사주채널 마스터 오케스트레이터
계정 × 시간대 기반으로 플랫폼별 포스팅 실행
"""
import os, sys, json, subprocess, datetime
from pathlib import Path

# ── 환경 로드 ─────────────────────────────────────────────────
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

NOW_KST = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
HOUR_KST = int(os.environ.get("HOUR_KST", NOW_KST.strftime("%H")))
ACCOUNT_ID = os.environ.get("ACCOUNT_ID", "sm")

with open(Path(__file__).parent.parent / "data" / "accounts.json", encoding="utf-8") as f:
    config = json.load(f)

account = next(a for a in config["accounts"] if a["id"] == ACCOUNT_ID)
time_slot = config["time_slots"].get(f"{HOUR_KST:02d}", config["time_slots"]["06"])
enabled_platforms = account["platforms"]

print(f"\n{'='*50}")
print(f"  {account['name']} | {NOW_KST.strftime('%H:%M')} KST | {time_slot['title']}")
print(f"{'='*50}")

# ── 플랫폼 → 스크립트 매핑 ───────────────────────────────────
PLATFORM_SCRIPTS = {
    "instagram":   "post_instagram.py",
    "facebook":    "post_facebook.py",
    "threads":     "post_threads.py",
    "twitter":     "post_twitter.py",
    "tiktok":      "tiktok_post.py",
    "youtube":     "post_youtube.py",
    "naver_blog":  "post_naver_blog.py",
    "naver_clip":  "post_naver_clip.py",
    "naver_jisik": "post_naver_jisik.py",
}

# ── 이 시간대에 실행할 플랫폼 결정 ──────────────────────────
target_platforms = time_slot["platforms"]
SCRIPTS_DIR = Path(__file__).parent

results = {}

def run_script(script_name: str, platform: str) -> bool:
    script_path = SCRIPTS_DIR / script_name
    if not script_path.exists():
        print(f"  ⚠️  스크립트 없음: {script_name}")
        return False

    env = {
        **os.environ,
        "ACCOUNT_ID": ACCOUNT_ID,
        "HOUR_KST": str(HOUR_KST),
    }

    # 계정별 시크릿을 일반 이름으로 매핑
    prefix = account["env_prefix"]
    secret_map = {
        "instagram": ["INSTAGRAM_ACCESS_TOKEN", "INSTAGRAM_USER_ID"],
        "facebook":  ["FACEBOOK_PAGE_ID", "FACEBOOK_PAGE_ACCESS_TOKEN"],
        "threads":   ["THREADS_ACCESS_TOKEN", "THREADS_USER_ID"],
        "twitter":   ["TWITTER_API_KEY", "TWITTER_API_SECRET", "TWITTER_ACCESS_TOKEN", "TWITTER_ACCESS_TOKEN_SECRET"],
        "tiktok":    ["TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET", "TIKTOK_REFRESH_TOKEN"],
        "youtube":   ["YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"],
        "naver_blog":  ["NAVER_CLIENT_ID", "NAVER_CLIENT_SECRET", "NAVER_ACCESS_TOKEN", "NAVER_REFRESH_TOKEN"],
        "naver_clip":  ["GMAIL_USER", "GMAIL_APP_PASSWORD"],
        "naver_jisik": ["NAVER_ID", "NAVER_PW"],
    }

    # 계정 prefix로 오버라이드
    for key in secret_map.get(platform, []):
        prefixed = os.environ.get(f"{prefix}_{key}", "")
        if prefixed:
            env[key] = prefixed

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        output = result.stdout + result.stderr
        success = result.returncode == 0
        print(f"  [{platform}] {'✅' if success else '❌'}")
        if output:
            for line in output.strip().split("\n"):
                print(f"    {line}")
        return success
    except subprocess.TimeoutExpired:
        print(f"  [{platform}] ⏱ 타임아웃")
        return False
    except Exception as e:
        print(f"  [{platform}] ❌ 오류: {e}")
        return False

# ── 1. 콘텐츠 생성 ───────────────────────────────────────────
print("\n[1/2] 콘텐츠 생성 중...")
gen_result = subprocess.run(
    [sys.executable, str(SCRIPTS_DIR / "content_gen_v2.py")],
    env={**os.environ, "ACCOUNT_ID": ACCOUNT_ID, "HOUR_KST": str(HOUR_KST)},
    capture_output=True, text=True, timeout=120,
)
print(gen_result.stdout)
if gen_result.returncode != 0:
    print(f"❌ 콘텐츠 생성 실패: {gen_result.stderr[:200]}")
    sys.exit(1)

# ── 2. 플랫폼 포스팅 ─────────────────────────────────────────
print(f"\n[2/2] 플랫폼 포스팅 ({', '.join(target_platforms)})...")

for platform in target_platforms:
    if not enabled_platforms.get(platform, False):
        print(f"  [{platform}] 비활성화 — 건너뜀")
        continue
    script = PLATFORM_SCRIPTS.get(platform, "")
    if script:
        results[platform] = run_script(script, platform)

# ── 결과 요약 ─────────────────────────────────────────────────
success_count = sum(1 for v in results.values() if v)
print(f"\n결과: {success_count}/{len(results)} 성공")
for platform, ok in results.items():
    print(f"  {'✅' if ok else '❌'} {platform}")
