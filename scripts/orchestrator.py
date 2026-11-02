"""
사주채널 마스터 오케스트레이터
계정 × 시간대 기반으로 플랫폼별 포스팅 실행
"""
import os, sys, json, subprocess, datetime
from pathlib import Path

# 카톡 알림 (없어도 계속 진행)
try:
    sys.path.insert(0, str(Path(__file__).parent))
    from kakao_notify import notify_post_progress, notify_post_content
    KAKAO_OK = True
except Exception:
    KAKAO_OK = False
    def notify_post_progress(*a, **kw): pass
    def notify_post_content(*a, **kw): pass

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

# 플랫폼 강제 지정 (workflow_dispatch 파라미터)
platforms_override = os.environ.get("PLATFORMS_OVERRIDE", "").strip()

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

# 영상 생성이 필요한 시간대
VIDEO_SLOTS = {"08", "14", "18"}

# ── 이 시간대에 실행할 플랫폼 결정 ──────────────────────────
if platforms_override:
    target_platforms = [p.strip() for p in platforms_override.split(",") if p.strip()]
else:
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
        "twitter":   ["TWITTER_API_KEY", "TWITTER_API_SECRET",
                      "TWITTER_ACCESS_TOKEN", "TWITTER_ACCESS_TOKEN_SECRET"],
        "tiktok":    ["TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET", "TIKTOK_REFRESH_TOKEN"],
        "youtube":   ["YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"],
        "naver_blog":  ["NAVER_CLIENT_ID", "NAVER_CLIENT_SECRET",
                        "NAVER_ACCESS_TOKEN", "NAVER_REFRESH_TOKEN"],
        "naver_clip":  ["GMAIL_USER", "GMAIL_APP_PASSWORD"],
        "naver_jisik": ["NAVER_ID", "NAVER_PW"],
    }

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
            timeout=180,
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
print("\n[1/3] 콘텐츠 생성 중...")
notify_post_progress(ACCOUNT_ID, time_slot["title"], "콘텐츠 생성 시작", "working")
gen_result = subprocess.run(
    [sys.executable, str(SCRIPTS_DIR / "content_gen_v2.py")],
    env={**os.environ, "ACCOUNT_ID": ACCOUNT_ID, "HOUR_KST": str(HOUR_KST)},
    capture_output=True, text=True, timeout=180,
)
print(gen_result.stdout)
if gen_result.returncode != 0:
    notify_post_progress(ACCOUNT_ID, time_slot["title"], "콘텐츠 생성 실패", "error", gen_result.stderr[:60])
    print(f"❌ 콘텐츠 생성 실패: {gen_result.stderr[:300]}")
    sys.exit(1)

# 생성된 메타 읽어서 포스팅 내용 카톡 전송 (진행상황과 분리)
_meta_path = SCRIPTS_DIR / "sns_output" / ACCOUNT_ID / "meta.json"
if _meta_path.exists():
    try:
        with open(_meta_path, encoding="utf-8") as _f:
            _m = json.load(_f)
        _c = _m.get("content", {})
        notify_post_content(
            ACCOUNT_ID, time_slot["title"],
            _m.get("topic", ""),
            _c.get("hook", ""),
            _c.get("main_text", ""),
            time_slot.get("platforms", []),
        )
        notify_post_progress(ACCOUNT_ID, time_slot["title"], "콘텐츠 생성 완료", "ok",
                             _c.get("theme", ""))
    except Exception as _e:
        notify_post_progress(ACCOUNT_ID, time_slot["title"], "콘텐츠 생성 완료", "ok")

# ── 2. 영상 생성 (해당 시간대) ────────────────────────────────
if f"{HOUR_KST:02d}" in VIDEO_SLOTS:
    video_script = SCRIPTS_DIR / "video_gen.py"
    if video_script.exists():
        print("\n[2/3] 영상 생성 중...")
        vid_result = subprocess.run(
            [sys.executable, str(video_script)],
            env={**os.environ, "ACCOUNT_ID": ACCOUNT_ID, "HOUR_KST": str(HOUR_KST)},
            capture_output=True, text=True, timeout=300,
        )
        print(vid_result.stdout)
        if vid_result.returncode != 0:
            print(f"  ⚠️ 영상 생성 실패 (포스팅은 계속): {vid_result.stderr[:300]}")
    else:
        print("\n[2/3] video_gen.py 없음 — 건너뜀")
else:
    print(f"\n[2/3] 영상 생성 불필요 ({HOUR_KST}시)")

# ── 3. 플랫폼 포스팅 ─────────────────────────────────────────
print(f"\n[3/3] 플랫폼 포스팅 ({', '.join(target_platforms)})...")

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

# ── 포스팅 로그 저장 (대시보드용) ────────────────────────────
LOG_PATH = Path(__file__).parent.parent / "data" / f"posting_log_{ACCOUNT_ID}.json"
try:
    meta_path_check = SCRIPTS_DIR / "sns_output" / ACCOUNT_ID / "meta.json"
    _c_data = {}
    _topic = ""
    if meta_path_check.exists():
        with open(meta_path_check, encoding="utf-8") as _f:
            _m2 = json.load(_f)
        _c_data = _m2.get("content", {})
        _topic = _m2.get("topic", "")

    # 카드 이미지를 data/images/ 에 복사해 GitHub Pages로 서빙
    _date_str = NOW_KST.strftime("%Y-%m-%d")
    _slot_key = time_slot.get("key", NOW_KST.strftime("%H"))
    _img_src = SCRIPTS_DIR / "sns_output" / ACCOUNT_ID / f"card_sq_{_date_str}.jpg"
    _img_dir = LOG_PATH.parent / "images" / ACCOUNT_ID
    _img_dir.mkdir(parents=True, exist_ok=True)
    _img_dest_name = f"card_{_date_str}_{_slot_key}.jpg"
    _img_dest = _img_dir / _img_dest_name
    _image_url = ""
    if _img_src.exists():
        import shutil as _sh
        _sh.copy2(str(_img_src), str(_img_dest))
        _image_url = f"https://shinmoney7-cyber.github.io/-/data/images/{ACCOUNT_ID}/{_img_dest_name}"
        print(f"✅ 카드 이미지 복사: {_img_dest_name}")

    # 슬라이드 이미지 목록도 저장 (대시보드 갤러리용)
    _slide_imgs = []
    if _m2 := (lambda: json.load(open(meta_path_check, encoding="utf-8")) if meta_path_check.exists() else {})():
        for sp in _m2.get("slides_vertical", []):
            _sp_path = Path(sp)
            if _sp_path.exists():
                _sp_dest = _img_dir / _sp_path.name.replace(f"_{_date_str}", f"_{_date_str}_{_slot_key}")
                import shutil as _sh2
                _sh2.copy2(str(_sp_path), str(_sp_dest))
                _slide_imgs.append(f"https://shinmoney7-cyber.github.io/-/data/images/{ACCOUNT_ID}/{_sp_dest.name}")

    log_entry = {
        "ts_kst": NOW_KST.strftime("%Y-%m-%d %H:%M"),
        "date": _date_str,
        "slot": time_slot.get("title", ""),
        "topic": _topic,
        "hook": _c_data.get("hook", ""),
        "main_text": _c_data.get("main_text", ""),
        "theme": _c_data.get("theme", ""),
        "instagram_caption": _c_data.get("instagram_caption", "")[:200],
        "threads_post": _c_data.get("threads_post", ""),
        "twitter_post": _c_data.get("twitter_post", ""),
        "platforms_ok": [p for p, v in results.items() if v],
        "platforms_fail": [p for p, v in results.items() if not v],
        "image_url": _image_url,
        "slide_urls": _slide_imgs,
    }

    existing = []
    if LOG_PATH.exists():
        try:
            with open(LOG_PATH, encoding="utf-8") as _f:
                existing = json.load(_f)
        except Exception:
            existing = []

    existing.insert(0, log_entry)
    existing = existing[:30]  # 최근 30개 유지

    LOG_PATH.parent.mkdir(exist_ok=True)
    with open(LOG_PATH, "w", encoding="utf-8") as _f:
        json.dump(existing, _f, ensure_ascii=False, indent=2)
    print(f"✅ 포스팅 로그 저장: {LOG_PATH.name}")
except Exception as _le:
    print(f"⚠️ 로그 저장 실패 (무시): {_le}")

# 플랫폼별 결과 카톡 알림 (진행상황)
ok_list = [p for p, v in results.items() if v]
fail_list = [p for p, v in results.items() if not v]
summary_detail = ""
if ok_list:
    summary_detail += f"✅{','.join(ok_list[:4])}"
if fail_list:
    summary_detail += f" ❌{','.join(fail_list[:3])}"
notify_post_progress(
    ACCOUNT_ID, time_slot["title"],
    f"포스팅 완료 {success_count}/{len(results)}",
    "ok" if success_count == len(results) else "error",
    summary_detail,
)
