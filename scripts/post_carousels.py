"""
캐러셀 자동 포스팅 스크립트
각 계정의 HTML 캐러셀을 Playwright로 캡처 → Typefully로 업로드 → 드래프트 생성

사용법:
  python3.13 scripts/post_carousels.py

필요 환경변수 (scripts/.env):
  TYPEFULLY_API_KEY=your_key_here

계정 정보:
  사주마루: social_set_id=348526, pages/carousel-sm.html
  사주보는언니: social_set_id=349146, pages/carousel-un.html
  사주마루77: social_set_id=349162, pages/carousel-77.html
"""

import os, sys, json, time, subprocess, requests
from pathlib import Path

# ── 환경변수 로드 ─────────────────────────────────────────────
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

API_KEY = os.environ.get("TYPEFULLY_API_KEY", "")
if not API_KEY:
    print("❌ TYPEFULLY_API_KEY 미설정 — scripts/.env 에 추가하세요")
    sys.exit(1)

# ── 설정 ─────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent
PAGES_DIR = BASE_DIR / "pages"
OUTPUT_DIR = BASE_DIR / "output" / "slides"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ACCOUNTS = [
    {
        "name": "사주마루",
        "social_set_id": 348526,
        "html_file": PAGES_DIR / "carousel-sm.html",
        "caption": "오늘의 사주 운세 🌟 #사주 #운세 #사주마루",
    },
    {
        "name": "사주보는언니",
        "social_set_id": 349146,
        "html_file": PAGES_DIR / "carousel-un.html",
        "caption": "오늘의 사주 운세 🌙 #사주 #운세 #사주보는언니",
    },
    {
        "name": "사주마루77",
        "social_set_id": 349162,
        "html_file": PAGES_DIR / "carousel-77.html",
        "caption": "오늘의 사주 운세 ⚡ #사주 #운세 #사주마루77",
    },
]

TYPEFULLY_BASE = "https://api.typefully.com/v1"
HEADERS = {
    "X-API-KEY": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

# ── Playwright 캡처 ───────────────────────────────────────────
def capture_slides(html_file: Path, account_name: str) -> list[Path]:
    """Playwright로 캐러셀 슬라이드를 PNG로 캡처"""
    from playwright.sync_api import sync_playwright

    slide_paths = []
    file_url = f"file://{html_file.resolve()}"

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )
        page = browser.new_page(viewport={"width": 1080, "height": 1080})
        page.goto(file_url, wait_until="networkidle")
        page.wait_for_timeout(1000)

        # 총 카드 수 확인
        total = page.evaluate("() => document.querySelectorAll('.card').length")
        total = max(total or 1, 1)
        print(f"  슬라이드 {total}장 감지")

        for slide_num in range(1, total + 1):
            # 활성 카드 캡처
            card = page.query_selector(".card.active")
            if not card:
                card = page.query_selector(".card")

            out_path = OUTPUT_DIR / f"{account_name}_slide{slide_num:02d}.png"
            if card:
                card.screenshot(path=str(out_path))
            else:
                page.screenshot(path=str(out_path))

            slide_paths.append(out_path)
            print(f"  📸 슬라이드 {slide_num} 캡처 → {out_path.name}")

            # 마지막 슬라이드면 다음 클릭 불필요
            if slide_num < total:
                next_btn = page.query_selector("#next")
                if next_btn:
                    next_btn.click()
                    page.wait_for_timeout(500)

        browser.close()

    return slide_paths


# ── Typefully 업로드 ──────────────────────────────────────────
def upload_image(social_set_id: int, image_path: Path) -> str | None:
    """이미지를 Typefully에 업로드하고 media_id 반환"""
    # 1. presigned URL 요청
    resp = requests.post(
        f"{TYPEFULLY_BASE}/uploads/",
        headers=HEADERS,
        json={"social_set_id": social_set_id, "file_name": image_path.name},
    )
    if resp.status_code not in (200, 201):
        print(f"  ❌ upload 요청 실패: {resp.status_code} {resp.text[:200]}")
        return None

    data = resp.json()
    upload_url = data.get("upload_url", "")
    media_id = data.get("media_id", "")

    if not upload_url or not media_id:
        print(f"  ❌ presigned URL 없음: {data}")
        return None

    # 2. S3에 파일 PUT (헤더 없이 raw bytes)
    with open(image_path, "rb") as f:
        put_resp = requests.put(upload_url, data=f)

    if put_resp.status_code not in (200, 204):
        print(f"  ❌ S3 업로드 실패: {put_resp.status_code}")
        return None

    # 3. 처리 완료 대기
    for _ in range(20):
        time.sleep(2)
        status_resp = requests.get(
            f"{TYPEFULLY_BASE}/uploads/{media_id}/",
            headers=HEADERS,
            params={"social_set_id": social_set_id},
        )
        if status_resp.status_code == 200:
            status_data = status_resp.json()
            status = status_data.get("status", "")
            if status == "ready":
                print(f"  ✅ 업로드 완료: {media_id}")
                return media_id
            elif status == "error":
                print(f"  ❌ 미디어 처리 오류: {status_data}")
                return None

    print(f"  ⚠️ 업로드 타임아웃: {media_id}")
    return media_id  # 타임아웃이어도 media_id 반환 시도


def create_draft(social_set_id: int, caption: str, media_ids: list[str]) -> dict | None:
    """Typefully 드래프트 생성"""
    payload = {
        "social_set_id": social_set_id,
        "platforms": {
            "threads": {
                "enabled": True,
                "posts": [{"text": caption, "media_ids": media_ids}],
            }
        },
    }
    resp = requests.post(f"{TYPEFULLY_BASE}/drafts/", headers=HEADERS, json=payload)
    if resp.status_code in (200, 201):
        return resp.json()
    print(f"  ❌ 드래프트 생성 실패: {resp.status_code} {resp.text[:300]}")
    return None


# ── 메인 ─────────────────────────────────────────────────────
def main():
    print("🌟 캐러셀 자동 포스팅 시작\n")

    for account in ACCOUNTS:
        name = account["name"]
        html_file = account["html_file"]
        social_set_id = account["social_set_id"]
        caption = account["caption"]

        print(f"━━━ {name} ━━━")

        if not html_file.exists():
            print(f"  ⚠️ HTML 파일 없음: {html_file}")
            continue

        # 1. 슬라이드 캡처
        print("  📷 슬라이드 캡처 중...")
        slide_paths = capture_slides(html_file, name)
        if not slide_paths:
            print("  ❌ 캡처된 슬라이드 없음")
            continue

        # 2. 이미지 업로드
        media_ids = []
        for path in slide_paths:
            print(f"  ⬆️  업로드: {path.name}")
            media_id = upload_image(social_set_id, path)
            if media_id:
                media_ids.append(media_id)

        if not media_ids:
            print("  ❌ 업로드된 이미지 없음")
            continue

        # 3. 드래프트 생성
        print(f"  📝 드래프트 생성 ({len(media_ids)}장)...")
        draft = create_draft(social_set_id, caption, media_ids)
        if draft:
            draft_id = draft.get("id", "")
            print(f"  ✅ 드래프트 생성 완료: {draft_id}\n")
        else:
            print("  ❌ 드래프트 생성 실패\n")

    print("🎉 모든 계정 처리 완료")


if __name__ == "__main__":
    main()
