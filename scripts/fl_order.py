#!/usr/bin/env python3
"""
Fortune LAB 단건 주문 자동화
사주마루 주문 데이터 → FL 단건 주문 자동 입력
"""
import json, sys, os
from pathlib import Path
from playwright.sync_api import sync_playwright

# .env 자동 로드
_env = Path(__file__).parent / ".env"
if _env.exists():
    for line in _env.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

FL_BASE  = "https://saju.coredev.co.kr"
FL_ID    = os.getenv("FL_ID", "")
FL_PW    = os.getenv("FL_PW", "")

# 사주마루 메뉴명 → FL 상품명
PRODUCT_MAP = {
    "성향·기질 분석":      "정통사주",
    "평생운":              "정통사주프리미엄",
    "연애운":              "연애사주",
    "배우자운·결혼운":     "연애사주",
    "재물운":              "재물사주",
    "건강운":              "프리미엄건강운세",
    "대운·세운":           "정통사주프리미엄",
    "부모운":              "프리미엄부모자식궁합",
    "자식운":              "프리미엄부모자식궁합",
    "형제간운":            "정통사주",
    "새해운세":            "2026년 신년운세",
    "월별운세":            "2026년 월별운세",
    "수능·입시운":         "수능운세",
    "재회운":              "재회운",
    "사업운":              "사업운세",
    "이혼·결별운":         "이혼운세",
    "도화살 전문분석":     "도화살",
    "이런 사람 만나지 마라": "짝사랑알아보기",
}


def place_order(order: dict) -> dict:
    """
    order = {
        "name": "홍길동",
        "gender": "여성",          # 여성 / 남성
        "cal_type": "양력",        # 양력 / 음력
        "year": 1990, "month": 1, "day": 15,
        "hour": 14, "minute": 30,  # 시간 모를 경우 None
        "product": "연애운",       # 사주마루 메뉴명
        "customer_email": "customer@example.com",
    }
    """
    fl_product = PRODUCT_MAP.get(order["product"], order["product"])
    print(f"[FL] 주문 시작: {order['name']} / {order['product']} → {fl_product}")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path="/opt/pw-browsers/chromium",
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        page = browser.new_page()

        try:
            # ── 1. 로그인 ──────────────────────────────────────────────
            page.goto(f"{FL_BASE}/login", wait_until="networkidle", timeout=30000)
            page.screenshot(path="/tmp/fl_1_login.png")

            # FL 로그인: 아이디(텍스트) + 비밀번호
            page.locator('input[type="text"], input[name="id"], input[name="username"]').first.fill(FL_ID)
            page.fill('input[type="password"]', FL_PW)
            page.click('button:has-text("로그인")')
            page.wait_for_load_state("networkidle", timeout=15000)
            page.screenshot(path="/tmp/fl_2_after_login.png")
            print(f"[FL] 로그인 완료: {page.url}")

            # ── 2. 단건 주문 페이지 ────────────────────────────────────
            page.goto(f"{FL_BASE}/order/single", wait_until="networkidle", timeout=20000)
            page.screenshot(path="/tmp/fl_3_order_page.png")

            # 페이지 소스 저장 (선택자 확인용)
            with open("/tmp/fl_order_page.html", "w", encoding="utf-8") as f:
                f.write(page.content())
            print("[FL] 주문 페이지 소스 저장됨 → /tmp/fl_order_page.html")

            # ── 3. 상품 선택 ───────────────────────────────────────────
            selects = page.locator("select").all()
            print(f"[FL] select 개수: {len(selects)}")
            for i, s in enumerate(selects):
                opts = s.locator("option").all_inner_texts()
                print(f"  select[{i}]: {opts[:5]}")

            # 첫 번째 select = 상품
            selects[0].select_option(label=fl_product)

            # ── 4. 이메일 ──────────────────────────────────────────────
            email_inputs = page.locator('input[type="email"]').all()
            if email_inputs:
                email_inputs[0].fill(order["customer_email"])
            else:
                page.locator('input[placeholder*="email"], input[placeholder*="이메일"]').first.fill(order["customer_email"])

            # ── 5. 이름 ───────────────────────────────────────────────
            page.locator('input[placeholder="홍길동"]').fill(order["name"])

            # ── 6. 성별 ───────────────────────────────────────────────
            gender_label = "여성" if "여" in str(order.get("gender", "여")) else "남성"
            selects[1].select_option(label=gender_label)

            # ── 7. 양/음력 ────────────────────────────────────────────
            cal_label = "음력" if "음" in str(order.get("cal_type", "양")) else "양력"
            selects[2].select_option(label=cal_label)

            # ── 8. 생년월일 ───────────────────────────────────────────
            page.locator('input[placeholder="1990"]').fill(str(order["year"]))
            page.locator('input[placeholder="1"]').fill(str(order["month"]))
            page.locator('input[placeholder="15"]').fill(str(order["day"]))

            # ── 9. 출생시간 ───────────────────────────────────────────
            if order.get("hour") is not None:
                page.locator('input[placeholder="14"]').fill(str(order["hour"]))
                page.locator('input[placeholder="30"]').fill(str(order.get("minute", 0)))
            else:
                page.locator('input[type="checkbox"]').first.check()

            page.screenshot(path="/tmp/fl_4_filled.png")

            # ── 10. 제출 ──────────────────────────────────────────────
            page.click('button[type="submit"]')
            page.wait_for_load_state("networkidle", timeout=20000)
            page.screenshot(path="/tmp/fl_5_result.png")
            final_url = page.url
            print(f"[FL] 주문 완료: {final_url}")

            return {"success": True, "url": final_url, "product": fl_product}

        except Exception as e:
            page.screenshot(path="/tmp/fl_error.png")
            print(f"[FL] 오류: {e}")
            return {"success": False, "error": str(e)}

        finally:
            browser.close()


if __name__ == "__main__":
    # 테스트 주문
    sample = {
        "name":           "테스트고객",
        "gender":         "여성",
        "cal_type":       "양력",
        "year":           1990,
        "month":          5,
        "day":            20,
        "hour":           None,  # 시간 모름
        "product":        "연애운",
        "customer_email": "shinmoney7@gmail.com",
    }
    if len(sys.argv) > 1:
        sample = json.loads(sys.argv[1])

    result = place_order(sample)
    print(json.dumps(result, ensure_ascii=False, indent=2))
