"""
네이버 지식인 자동 답변 (Playwright 브라우저 자동화)
공식 API 없음 — 로그인 후 질문 검색 → 답변 게시
필요 GitHub Secrets: NAVER_ID, NAVER_PW
"""
import os, json, sys, time, random
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# ── 환경 로드 ─────────────────────────────────────────────────
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

NAVER_ID = os.environ.get("NAVER_ID", "")
NAVER_PW = os.environ.get("NAVER_PW", "")
ACCOUNT_ID = os.environ.get("ACCOUNT_ID", "sm")

if not NAVER_ID or not NAVER_PW:
    print("⚠️  NAVER_ID / NAVER_PW 미설정 — 건너뜀")
    sys.exit(0)

# ── meta.json 로드 ────────────────────────────────────────────
meta_path = Path(__file__).parent / "sns_output" / ACCOUNT_ID / "meta.json"
if not meta_path.exists():
    meta_path = Path(__file__).parent / "sns_output" / "meta.json"

with open(meta_path, encoding="utf-8") as f:
    meta = json.load(f)

content = meta["content"]
answer_text = content.get("jisik_answer", "")
account_name = meta.get("account", {}).get("name", "사주마루")

if not answer_text:
    print("⚠️  지식인 답변 내용 없음 — 건너뜀")
    sys.exit(0)

# 답변 끝에 채널 홍보 추가
CTA_SUFFIX = f"\n\n더 자세한 사주 분석은 {account_name} 채널에서 무료로 확인하세요 🌟"
full_answer = answer_text + CTA_SUFFIX

# ── 검색 키워드 ───────────────────────────────────────────────
SEARCH_KEYWORDS = [
    "오늘 사주 운세",
    "사주 보는 방법",
    "사주 궁합",
    "이번주 운세",
    "사주 좋은날",
    "사주 무료 상담",
    "사주 띠별 운세",
    "사주 직업운",
    "사주 재물운",
]
keyword = random.choice(SEARCH_KEYWORDS)

MAX_ANSWERS = 3  # 1회 실행당 최대 답변 수 (스팸 방지)
answered = 0

def human_type(page, selector: str, text: str):
    """자연스러운 타이핑 시뮬레이션"""
    el = page.query_selector(selector)
    if not el:
        return
    el.click()
    for char in text:
        el.type(char, delay=random.randint(30, 90))

with sync_playwright() as p:
    browser = p.chromium.launch(
        executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
        headless=True,
        args=["--no-sandbox", "--disable-setuid-sandbox", "--lang=ko-KR"],
    )
    context = browser.new_context(
        locale="ko-KR",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    )
    page = context.new_page()

    try:
        # 1. 네이버 로그인
        print("  로그인 중...")
        page.goto("https://nid.naver.com/nidlogin.login", wait_until="domcontentloaded")
        time.sleep(1)

        # ID/PW 입력
        page.evaluate(f"document.getElementById('id').value = '{NAVER_ID}'")
        page.evaluate(f"document.getElementById('pw').value = '{NAVER_PW}'")
        time.sleep(0.5)
        page.click("#log\\.login")
        time.sleep(3)

        # 캡차 체크
        if "captcha" in page.url or "nidlogin" in page.url:
            print("  ⚠️ 캡차 또는 로그인 실패 — 건너뜀")
            browser.close()
            sys.exit(0)

        print("  ✅ 로그인 성공")

        # 2. 지식인 검색
        jisik_url = f"https://kin.naver.com/search/list.naver?query={keyword.replace(' ', '+')}&dirId=0&section=kin"
        page.goto(jisik_url, wait_until="domcontentloaded")
        time.sleep(2)

        # 3. 미답변 질문 찾기
        questions = page.query_selector_all(".question_list .question_item a, li.question_item a[href*='/detail/']")
        print(f"  질문 {len(questions)}개 발견")

        for q in questions[:10]:
            if answered >= MAX_ANSWERS:
                break

            q_url = q.get_attribute("href") or ""
            if not q_url.startswith("http"):
                q_url = "https://kin.naver.com" + q_url

            # 개별 질문 페이지
            page.goto(q_url, wait_until="domcontentloaded")
            time.sleep(1.5)

            # 이미 답변된 질문인지 확인 (채택 완료 = 건너뜀)
            is_closed = page.query_selector(".answer_complete, .btn_adopt_sel")
            if is_closed:
                continue

            # 답변 작성 버튼
            write_btn = page.query_selector("a[href*='write'], button.btn_answer, a.btn_answer")
            if not write_btn:
                continue

            write_btn.click()
            time.sleep(2)

            # 답변 입력창
            answer_area = page.query_selector("textarea#answer, .kin-editor-area, div[contenteditable='true']")
            if not answer_area:
                continue

            answer_area.click()
            time.sleep(0.5)
            page.keyboard.type(full_answer, delay=20)
            time.sleep(1)

            # 게시 버튼
            submit_btn = page.query_selector("button[type='submit'], .btn_send, .btn_submit")
            if submit_btn:
                submit_btn.click()
                time.sleep(2)
                answered += 1
                print(f"  ✅ 답변 게시 완료 ({answered}/{MAX_ANSWERS}): {q_url[:60]}...")
                time.sleep(random.randint(5, 15))

    except PWTimeout as e:
        print(f"  ⚠️ 타임아웃: {e}")
    except Exception as e:
        print(f"  ❌ 오류: {e}")
    finally:
        browser.close()

print(f"✅ 지식인 답변 완료: {answered}개")
meta["jisik_answered"] = answered
with open(meta_path, "w", encoding="utf-8") as f:
    json.dump(meta, f, ensure_ascii=False, indent=2)
