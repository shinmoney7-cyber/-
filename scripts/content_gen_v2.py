"""
사주채널 통합 콘텐츠 생성기 v3
- 탑 수익 크리에이터 전략: 바이럴 훅 + 카카오 상담 CTA + 알고리즘 최적화
- 3계정 × 시간대별 × 10개 토픽 차별화
- 플랫폼별 포맷 + 프리미엄 이미지 카드 (황금빛 신비 스타일)
"""
import os, json, sys, datetime, re, math
import anthropic
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pathlib import Path

# ── 환경 로드 ─────────────────────────────────────────────────
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
if not ANTHROPIC_KEY:
    print("❌ ANTHROPIC_API_KEY 미설정")
    sys.exit(1)

client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

# ── 설정 ─────────────────────────────────────────────────────
NOW_UTC = datetime.datetime.utcnow()
NOW_KST = NOW_UTC + datetime.timedelta(hours=9)
TODAY_STR = NOW_KST.strftime("%Y-%m-%d")
HOUR_KST = int(os.environ.get("HOUR_KST", NOW_KST.strftime("%H")))

WEEKDAYS_KR = ["월요일","화요일","수요일","목요일","금요일","토요일","일요일"]
TODAY_KR = f"{NOW_KST.strftime('%m월 %d일')} {WEEKDAYS_KR[NOW_KST.weekday()]}"
YEAR_KR = NOW_KST.strftime("%Y년")

ACCOUNT_ID = os.environ.get("ACCOUNT_ID", "sm")

with open(Path(__file__).parent.parent / "data" / "accounts.json", encoding="utf-8") as f:
    config = json.load(f)

account = next(a for a in config["accounts"] if a["id"] == ACCOUNT_ID)
time_slot = config["time_slots"].get(f"{HOUR_KST:02d}", config["time_slots"]["08"])
mono = config.get("monetization", {})

WEEKDAY = NOW_KST.weekday()
TOPIC = time_slot["topic_rotation"][WEEKDAY % len(time_slot["topic_rotation"])]

OUT_DIR = Path(__file__).parent / "sns_output" / ACCOUNT_ID
OUT_DIR.mkdir(parents=True, exist_ok=True)

print(f"[{NOW_KST.strftime('%H:%M')} KST] {account['name']} — {time_slot['title']} / {TOPIC} 콘텐츠 생성")

# ── 카카오/폼 CTA 세팅 ──────────────────────────────────────
KAKAO_CTA  = mono.get("cta_kakao",  "💬 카카오 무료상담 바로가기")
FORM_CTA   = mono.get("cta_form",   "📋 무료 사주 신청")
FORM_URL   = mono.get("consultation_form", "forms.gle/t2sSNES5NYow77vz5")
STORE_URL  = mono.get("smartstore", "smartstore.naver.com/sajumaru")

# ── 계정 × 토픽 차별화 (탑 크리에이터 전략) ─────────────────
TOPIC_ANGLE = {
    "sm": {
        "생활용품":   "일상 필수 생활용품 가성비 발굴. 직접 써본 솔직 리뷰. 쿠팡 vs 다이소 비교.",
        "주방용품":   "주방 효율 높이는 아이템. 요리·설거지 시간 단축 템. 내구성·가격 팩트체크.",
        "인테리어소품": "저렴하게 감성 인테리어 완성. IKEA 대체 아이템. 공간별 활용 소품 추천.",
        "수납정리":   "집 정리 완성하는 수납템. 공간 활용 극대화. 사이즈·재질 비교 팁.",
        "청소용품":   "청소 시간 반으로 줄이는 도구. 친환경 세제 성분 분석. 브랜드별 세정력 비교.",
        "욕실용품":   "욕실 공간 깔끔하게 만드는 수납·도구. 습기 곰팡이 방지 아이템. 가격 비교.",
        "소형가전":   "주방·생활 소형가전 스펙 비교. 실사용 에너지 절약 효과. 최저가 구매 타이밍.",
        "침구/커튼":  "수면 질 높이는 침구 선택법. 계절별 소재 추천. 세탁 편의성·내구성 비교.",
        "조명":       "공간 분위기 바꾸는 조명 추천. 색온도·밝기 선택법. DIY 셀프 조명 교체 팁.",
        "식물/원예":  "초보 식물 키우기 필수 아이템. 물주기 자동화 도구. 공기정화 식물 추천 & 관리법.",
    },
    "nw": {
        "스킨케어/세럼":    "피부 고민별 세럼 성분 분석. EWG 등급 확인법. 가성비 vs 프리미엄 비교. 화해 평점 팩트체크.",
        "선크림/자외선차단": "SPF/PA 등급 차이 설명. 백탁 없는 선크림 찾기. 실내·야외 용도별 추천.",
        "클렌징":           "저자극 성분 클렌저 비교. 이중세안 필요/불필요 판단. 피부 타입별 클렌징 방법.",
        "토너/미스트":      "수분 공급 루틴 정립. 토너패드 vs 일반 토너 차이. 성분 흡수율 높이는 순서.",
        "마스크팩":         "시트팩 vs 워시오프 팩 비교. 주 몇 회 사용이 맞는지. 가성비 마스크팩 순위.",
        "메이크업":         "피부 표현 제품 성분·지속력 비교. 톤업·쿠션·파운데이션 차이. 메이크업 순서 꿀팁.",
        "헤어케어":         "두피 건강 샴푸 성분 분석. 머리 빠짐·손상모 케어 아이템. 쿠팡 vs 올리브영 가격 비교.",
        "향수/바디케어":    "향수 지속력 테스트 결과. 바디로션·오일 흡수 속도 비교. 데일리 vs 특별일 향 추천.",
        "뷰티기기":         "LED 마스크·갈바닉·초음파 기기 효과 팩트체크. 가정용 뷰티기기 가성비 순위.",
        "네일아트":         "젤네일 키트 성분 안전성. 초보 네일 팁. 올리브영 단독 vs 쿠팡 가격 비교.",
    },
    "un": {
        "띠별운세":  "언니가 오늘 우리 띠별 에너지 솔직하게 봐줄게 🥰 진짜 맞아서 소름 돋을 거야.",
        "재물운":    "언니가 알려주는 오늘 돈 들어오는 타이밍! 저축 vs 투자 언제 해야 해?",
        "재회운":    "전남친한테서 연락 올 수 있어 💕 아니면 새 인연? 언니가 미리 알려줄게.",
        "합격운":    "시험 앞둔 우리 동생들 언니가 합격 타이밍 봐줄게 🍀 집중력 오르는 날이야.",
        "이직승진운": "직장에서 인정받고 싶지? 이직 타이밍 잘못 잡으면 후회해. 언니가 짚어줄게.",
        "사업운":    "창업 생각 중이야? 언니가 솔직하게 말해줄게, 지금 시작해도 돼 말아야 해?",
        "건강운":    "몸 관리 소홀하면 안 돼 언니가 걱정돼 😥 오늘 조심해야 할 신체 부위 있어.",
        "궁합운":    "그 사람이랑 진짜 잘 맞아? 궁합 좋은 건지 나쁜 건지 언니가 봐줄게 💕",
        "이사운":    "이사 언제 해야 행운 따라와? 언니가 좋은 날 방향 골라줄게 🏠",
        "부모운":    "부모님이랑 관계 어때? 효도할 타이밍이야 💝 건강 챙겨드려.",
    },
    "s77": {
        "띠별운세":  "내 띠 오늘 어떰? 직빵으로 알려드림 ㅋ (진짜 맞음)",
        "재물운":    "돈 들어오냐 안 오냐 오늘 결론만 말함 💸 모르면 손해임",
        "재회운":    "걔한테 연락 올지 안 올지 사주로 봄 (실화임) 댓글에 띠 적어",
        "합격운":    "합격운 있음 없음 5초만에 알려줌 ⚡ 이거 알면 진짜 다름",
        "이직승진운": "이직해야 함 말아야 함 지금 당장 사주로 확인 🔥",
        "사업운":    "창업해도 되는 사주 vs 망하는 사주 차이 알려드림 (반박불가)",
        "건강운":    "건강 무시하지 마 진짜로 📢 오늘 이거 하면 진짜 위험함",
        "궁합운":    "걔랑 진짜 맞음? 궁합 나쁜 거 모르고 사귀면 큰일남 👀",
        "이사운":    "이사 잘못 타이밍 잡으면 운 다 날아감 ㅋ 맞는 날짜 알려드림",
        "부모운":    "부모님이랑 요즘 어떰? 관계운 솔직하게 봐드림 (눈물 주의)",
    },
}

TOPIC_GUIDE = TOPIC_ANGLE.get(ACCOUNT_ID, {}).get(TOPIC, TOPIC)

channel_type = account.get("channel_type", "saju")

# 쇼핑 채널은 account["topics"] 사용, saju는 time_slot 기반
if channel_type == "shopping":
    _topics = account.get("topics", ["오늘의픽"])
    TOPIC = _topics[WEEKDAY % len(_topics)]
    TOPIC_GUIDE = TOPIC_ANGLE.get(ACCOUNT_ID, {}).get(TOPIC, TOPIC)
    FORM_URL = account.get("shopping_links", {}).get("coupang_partners", "coupang.com/sabolkka")

# ── 탑 수익 크리에이터 훅 공식 ───────────────────────────────
HOOK_FORMULAS = """
훅 공식 (탑 사주 크리에이터 바이럴 패턴):
1. 숫자형: "이런 사람 3가지 특징", "2026년 이 띠 무조건 봐야 함"
2. 충격/반전형: "사주에서 이게 보이면 진짜 조심해야 해", "이거 모르면 손해"
3. 공감형: "이 경험 있는 사람 손 들어봐", "왜 나만 이런 것 같지라고 느낌 때"
4. 시리즈/궁금증형: "내 사주에 이게 있으면 (다음 편에 계속)", "파트2에서 다 알려줌"
5. 직접 타겟형: "1990년생 지금 당장 확인해", "이 달 생 무조건 달라짐"
6. 비교형: "운이 트인 사람 vs 막힌 사람 차이", "되는 사람과 안 되는 사람"
"""

PLATFORM_STRATEGY = f"""
플랫폼별 탑 수익 전략:
- 인스타그램: 저장(Save) 유도 ("나중에 볼게요 저장해!") + 캐러셀 첫 장 훅
- 틱톡/릴스: 처음 3초에 결론 먼저 ("오늘 이 띠 완전 대박납니다") + 댓글 유도 ("띠 적으면 봐줄게")
- 유튜브: 제목에 숫자+감성+날짜 ("2026 이 달 이 사람 무조건 뜸")
- 쓰레드: 연속 쓰레드 (+이어쓰기) 형식으로 궁금증 유발
- 네이버 블로그: 제목에 정확한 날짜+키워드 ("2026년 10월 오늘의 사주 무료 운세")
- 네이버 지식인: 전문적 답변 + 마지막에 자연스럽게 채널 유도

수익 전환 CTA (중요도 순):
1. 카카오 유료상담: 건당 30만원~90만원 (가장 수익 높음)
2. 네이버 스마트스토어: 사주책·상담권 판매
3. 유튜브 멤버십: 월 정기 수익
4. 무료 폼 → 상담 전환 퍼널
"""

PROMPT = f"""당신은 {account['name']} 채널의 한국 최상위 사주 SNS 크리에이터입니다.
실제 월 1000만원 이상 버는 사주 크리에이터들이 쓰는 전략으로 콘텐츠를 작성하세요.

페르소나: {account['persona']}
오늘: {TODAY_KR} ({YEAR_KR})
현재 슬롯: {time_slot['title']}
오늘의 토픽: {TOPIC}
접근 방식: {TOPIC_GUIDE}

{HOOK_FORMULAS}

{PLATFORM_STRATEGY}

【각 계정 고유 목소리 필수】
- 사주마루(sm): 학술적·권위있는 문체, 자평명리학 용어 자연스럽게, 신뢰감
- 사주보는언니(un): 따뜻한 언니 말투, 이모지 적극 사용, 여성 공감 강조
- 사주마루77(s77): Z세대 말투(ㅋ,ㄹㅇ,실화), 밈·유머, 짧고 직설적

수익 키워드 (자연스럽게 포함):
- 고CPM: "무료사주", "사주상담", "운세{NOW_KST.year}", "오늘운세", "사주팔자풀이"
- 검색량: "사주 무료", "운세 보기", "오늘 내 운세", "생년월일 사주"

CTA 링크:
- 카카오: {KAKAO_CTA}
- 무료폼: {FORM_URL}
- 스토어: {STORE_URL}

아래 JSON만 출력 (```없이, 설명없이):

{{
  "theme": "오늘의 사주 테마 (8자 이내, 감성적)",
  "zodiac_sign": "오늘 특히 강한 지지 (자/축/인/묘/진/사/오/미/신/유/술/해 중 하나)",
  "lucky_element": "오늘의 행운 요소 (색상·숫자·방향·음식 중 2가지)",

  "hook": "바이럴 훅 문구 (15자 이내, 위 훅 공식 중 하나 활용, 숫자나 의문형 포함)",
  "main_text": "본문 4줄\\n각 줄 30자 이내\\n사주 원리 근거 포함\\n마지막 줄에 희망적 조언",
  "cta": "카카오 상담 유도 행동문 (20자 이내, 무료/지금/바로 중 하나 포함)",

  "instagram_caption": "인스타 캡션 280자: 저장 유도 오프닝('이거 저장해두면 나중에 써먹어') + 핵심 내용 + {KAKAO_CTA} + 해시태그 20개 (#사주 #운세 #무료사주 #오늘운세 #사주상담 #사주팔자 #운세2026 #AI사주 #오늘의운세 #사주보기 포함)",
  "facebook_post": "페이스북 포스트 300자: 공유 유도 '공유하면 복이 와요' + 내용 + {FORM_URL} 링크 포함",
  "threads_post": "쓰레드 포스트 200자: 대화체 + '댓글에 띠 적으면 봐줄게' 또는 질문으로 마무리",
  "twitter_post": "트위터 130자: 임팩트있는 훅 + 핵심 1줄 + #사주 #운세 #오늘운세",

  "tiktok_hook": "틱톡 첫 3초 자막 (8자 이내, 결론 먼저, 충격 or 궁금증)",
  "tiktok_script": "틱톡/릴스 65초 스크립트\\n한 문장씩 줄바꿈\\n[0-3초] 충격 훅\\n[4-55초] 핵심 내용 (구체적 사주 원리 근거 포함)\\n[56-65초] 카카오 상담 CTA",

  "youtube_title": "유튜브 제목 50자: [{NOW_KST.year} 운세] 숫자+감성+클릭유도 (예: [2026 10월 운세] 이 띠 완전 뒤집어짐 🔮)",
  "youtube_description": "유튜브 설명 600자:\\n📌 챕터: 00:00 오프닝 / 00:08 오늘의 운세 분석 / 00:45 행운 요소 / 01:00 CTA\\n🔮 고CPM키워드 5개 자연삽입\\n💬 카카오 유료상담: {KAKAO_CTA}\\n📋 무료폼: {FORM_URL}\\n🛒 사주책/상담권: {STORE_URL}\\n#사주 #운세 #무료사주",
  "youtube_script": "유튜브 쇼츠 대본 65초\\nTTS 구어체\\n[0-5초] '안녕하세요 {account['name']}입니다' + 오늘 핵심 내용 예고\\n[6-55초] 사주 분석 (원리+근거+실용 조언)\\n[56-65초] 구독+카카오상담 CTA",

  "naver_blog_title": "네이버 블로그 SEO 제목 45자: '{TODAY_KR}' + '무료사주' or '오늘운세' + 토픽 키워드 포함",
  "naver_blog_content": "블로그 본문 2000자 이상:\\n## {TODAY_KR} {TOPIC} 사주 운세\\n(도입: 오늘의 에너지 설명 300자)\\n## 오늘의 핵심 사주 풀이\\n(분석 500자: 전문 용어 자연 삽입)\\n## {account['name']} 무료 상담 안내\\n(CTA 200자: {KAKAO_CTA} + {FORM_URL})\\n## 오늘의 행운 포인트\\n(행운 요소+방향+색상 200자)\\n## 이런 분께 추천해요\\n(타겟 독자층 명시 + 키워드 5개 삽입 200자)\\n(마무리: 따뜻한 응원 + {FORM_URL} CTA)",
  "naver_clip_hook": "네이버 클립 훅 (6자 이내, 강렬)",

  "jisik_question": "{TODAY_KR} 실제로 많이 검색될 사주/{TOPIC} 관련 질문 1개",
  "jisik_answer": "지식인 전문 답변 450자: 실질적 사주 원리 설명 + 구체적 조언 + 마지막에 '{account['name']} 채널에서 무료로 더 자세히 알아보세요' 자연스럽게",

  "slide_texts": [
    "슬라이드1 훅 텍스트 (10자 이내)",
    "슬라이드2 핵심 포인트 (15자 이내)",
    "슬라이드3 상세 내용 (15자 이내)",
    "슬라이드4 행운 요소 (10자 이내)",
    "슬라이드5 CTA (10자 이내)"
  ],
  "hashtags": "#사주 #운세 #무료사주 #오늘운세 #사주상담 #사주팔자 #운세2026 #AI사주 #{account['handle']} #사주보기 #{TOPIC.replace(' ','')} #오늘의운세 #사주풀이 #무료운세 #생년월일사주"
}}"""

SHOPPING_PROMPT = f"""당신은 {account['name']} 채널의 한국 최고 쇼핑 쇼츠 크리에이터입니다.
직접 써본 진짜 후기, 핫딜 발굴, 가성비 분석으로 월 1000만원 이상 버는 전략으로 콘텐츠를 작성하세요.

페르소나: {account['persona']}
오늘: {TODAY_KR}
카테고리: {TOPIC}
시간대: {time_slot['title']}

훅 공식 (쇼핑 크리에이터 바이럴 패턴):
1. 가격 충격형: "이거 {TOPIC} 분야 가성비 끝판왕이에요", "3만원인데 10만원짜리보다 나아요"
2. 솔직 후기형: "직접 3개월 써봤는데 솔직히 말할게요", "이거 유명한데 진짜 맞아요?"
3. 비교형: "쿠팡 vs 네이버쇼핑 어디가 더 싸요?", "비싼 거 vs 싼 거 차이 있어요?"
4. 급박형: "오늘만 이 가격이에요", "재고 얼마 없어요"
5. 정보형: "{TOPIC} 고를 때 이것만 봐요", "이거 모르고 사면 후회해요"

아래 JSON만 출력 (```없이, 설명없이):

{{
  "product_name": "오늘 소개할 대표 상품명 (구체적, 예: 코렐 접시 6P세트 / 닥터자르트 세라마이딘 세럼)",
  "price_range": "가격대 (예: 12,900원~28,000원)",
  "where_to_buy": "구매처 (쿠팡/네이버쇼핑/올리브영 등)",
  "hook": "첫 3초 훅 문구 (15자 이내, 숫자나 결론 포함)",
  "key_points": ["포인트1 (20자 이내)", "포인트2 (20자 이내)", "포인트3 (20자 이내)"],
  "honest_review": "솔직 한줄 평 (30자 이내, 단점 포함 필수 — 단점 없으면 신뢰 하락)",

  "instagram_caption": "인스타 캡션 250자: 저장 유도 오프닝 + 상품 핵심 + 가격 + #쇼핑 #쇼핑추천 #가성비 #오늘의픽 #쇼핑스타그램 #살까말까 #{account['handle']} #핫딜 #쿠팡 #{TOPIC.replace('/','').replace(' ','')} 포함",
  "threads_post": "쓰레드 200자: 대화체 + 구매 고민 공감 + '댓글에 써주세요' 유도",

  "tiktok_hook": "틱톡 첫 3초 자막 (8자 이내, 결론 먼저)",
  "tiktok_script": "틱톡/릴스 60초 스크립트 (한 문장씩 줄바꿈)\\n[0-3초] 훅: 이게 얼마인줄 알아요?\\n[4-45초] 상품 소개+핵심 포인트 3가지\\n[46-55초] 솔직 후기 (단점 포함해야 신뢰)\\n[56-60초] 구매 링크 CTA",

  "youtube_title": "유튜브 제목 50자: 가격+상품+클릭유도 (예: 이거 9,900원이라고요? {TOPIC} 인생템 발굴했어요)",
  "youtube_script": "유튜브 쇼츠 대본 60초 (TTS 구어체)\\n[0-5초] '안녕하세요 {account['name']}입니다' + 오늘 상품 예고\\n[6-50초] 상품 소개 + 장단점 + 가격 비교\\n[51-60초] 구매 링크 + 구독 CTA",

  "naver_blog_title": "네이버 블로그 SEO 제목 45자: '{TODAY_KR}' + 상품명 + '솔직후기' or '가성비' + '{TOPIC}' 포함",
  "naver_blog_content": "블로그 본문 1500자:\\n## {TODAY_KR} {TOPIC} 추천 아이템\\n(도입: 왜 이 상품인지 200자)\\n## 상품 스펙 & 가격\\n(스펙 + 가격 + 구매처 300자)\\n## 솔직 후기 (장점 3개 + 단점 1개)\\n(진짜 후기 500자: 단점 숨기면 신뢰 하락)\\n## 이런 분께 추천해요\\n(타겟 독자층 200자)\\n## 구매 링크\\n(CTA + 쿠팡/네이버쇼핑 유도)\\n\\n※ {account.get('shopping_links', {{}}).get('affiliate_notice', '')}",

  "naver_clip_hook": "네이버 클립 훅 (6자 이내, 가격이나 특징 강조)",

  "slide_texts": [
    "슬라이드1: 상품명 + 가격 (10자 이내)",
    "슬라이드2: 핵심 포인트1 (15자 이내)",
    "슬라이드3: 핵심 포인트2 (15자 이내)",
    "슬라이드4: 솔직 단점 (10자 이내)",
    "슬라이드5: 구매 유도 CTA (10자 이내)"
  ],
  "hashtags": "#쇼핑 #쇼핑추천 #가성비 #{TOPIC.replace('/','').replace(' ','')} #핫딜 #쿠팡 #네이버쇼핑 #{account['handle']} #살까말까 #오늘의픽 #쇼핑스타그램 #가성비템 #리뷰 #쇼츠"
}}"""

# API 호출
msg = client.messages.create(
    model="claude-haiku-4-5",
    max_tokens=3000,
    messages=[{"role": "user", "content": SHOPPING_PROMPT if channel_type == "shopping" else PROMPT}]
)

raw = msg.content[0].text.strip()
raw = re.sub(r"^```json?\s*", "", raw)
raw = re.sub(r"```\s*$", "", raw)
content = json.loads(raw.strip())

# 쇼핑 채널: 이미지 생성 함수 호환용 필드 정규화
if channel_type == "shopping":
    content.setdefault("main_text", "\n".join(content.get("key_points", [])))
    content.setdefault("zodiac_sign", "자")
    content.setdefault("lucky_element", content.get("honest_review", ""))
    content.setdefault("cta", f"💰 {content.get('price_range', '')}  {content.get('where_to_buy', '쿠팡')}")
    print(f"✅ 콘텐츠 생성 완료: {content.get('product_name', '')} | 훅: {content.get('hook', '')[:20]}")
else:
    print(f"✅ 콘텐츠 생성 완료: {content.get('theme', '')} | 훅: {content.get('hook', '')[:20]}")

# ── 프리미엄 이미지 카드 생성 (황금빛 신비 스타일) ───────────
def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def draw_radial_glow(draw, cx, cy, r_max, color_inner, color_outer, steps=80):
    """황금빛 방사형 글로우 효과"""
    for i in range(steps, 0, -1):
        r = int(r_max * i / steps)
        t = i / steps
        c = tuple(int(color_inner[j] * t + color_outer[j] * (1 - t)) for j in range(3))
        alpha = int(60 * (i / steps) ** 2)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*c, alpha))

def draw_circle_decorations(draw, cx, cy, r, color, n=8):
    """팔괘/원형 장식 점"""
    for i in range(n):
        angle = 2 * math.pi * i / n
        x = cx + int(r * math.cos(angle))
        y = cy + int(r * math.sin(angle))
        draw.ellipse([x - 6, y - 6, x + 6, y + 6], fill=(*color, 180))

def draw_hex_lines(draw, cx, cy, r, color, n=6):
    """육각형 별빛 라인"""
    pts = []
    for i in range(n):
        angle = math.pi / 2 + 2 * math.pi * i / n
        pts.append((cx + int(r * math.cos(angle)), cy + int(r * math.sin(angle))))
    for i in range(n):
        a, b = pts[i], pts[(i + 2) % n]
        draw.line([a, b], fill=(*color, 60), width=1)

def wrap_text(text, max_chars):
    """긴 텍스트를 줄로 분리"""
    if not text:
        return []
    words = list(text)
    lines, cur = [], ""
    for ch in words:
        if len(cur) >= max_chars:
            lines.append(cur)
            cur = ch
        else:
            cur += ch
    if cur:
        lines.append(cur)
    return lines

def get_fonts(sizes=(90, 58, 36, 28)):
    paths = [
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.otf",
        "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
    ]
    fonts = []
    for sz in sizes:
        loaded = False
        for p in paths:
            try:
                fonts.append(ImageFont.truetype(p, sz))
                loaded = True
                break
            except Exception:
                pass
        if not loaded:
            fonts.append(ImageFont.load_default())
    return fonts

def make_image_card(content: dict, account: dict, size=(1080, 1080)) -> Path:
    """프리미엄 사주 이미지 카드 — 황금빛 신비 스타일"""
    W, H = size
    bg = hex_to_rgb(account["bg"])
    accent = hex_to_rgb(account["accent"])

    # 베이스 레이어 (다크 배경)
    base = Image.new("RGBA", (W, H), (*bg, 255))
    glow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow_layer)

    # 황금빛 방사형 글로우 (하단 1/3)
    draw_radial_glow(gd, W // 2, H - 200, 480, accent, (0, 0, 0), steps=100)
    # 상단 소형 글로우
    draw_radial_glow(gd, W // 2, 180, 260, accent, (0, 0, 0), steps=60)

    base = Image.alpha_composite(base, glow_layer)

    # 원형 장식 레이어
    deco_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dd = ImageDraw.Draw(deco_layer)
    draw_circle_decorations(dd, W // 2, H // 2, 400, accent, n=12)
    draw_circle_decorations(dd, W // 2, H // 2, 340, accent, n=8)
    # 외곽 원
    r_outer = 420
    dd.ellipse([W//2 - r_outer, H//2 - r_outer, W//2 + r_outer, H//2 + r_outer],
               outline=(*accent, 30), width=1)
    dd.ellipse([W//2 - 300, H//2 - 300, W//2 + 300, H//2 + 300],
               outline=(*accent, 20), width=1)
    # 육각 별빛
    draw_hex_lines(dd, W // 2, H // 2, 350, accent)

    base = Image.alpha_composite(base, deco_layer)
    draw = ImageDraw.Draw(base)

    font_xl, font_lg, font_md, font_sm = get_fonts((90, 58, 36, 28))

    # ─ 상단: 계정명 ─────────────────────────────
    draw.text((W // 2, 70), account["name"], fill=(*accent, 230), font=font_sm, anchor="mm")
    # 구분선
    draw.line([(W//2 - 80, 95), (W//2 + 80, 95)], fill=(*accent, 80), width=1)
    # 날짜
    draw.text((W // 2, 130), TODAY_KR, fill=(180, 180, 210), font=font_sm, anchor="mm")

    # ─ 중앙 상단: 지지 이모지 ────────────────────
    zodiac_map = {"자":"🐭","축":"🐂","인":"🐯","묘":"🐰","진":"🐲","사":"🐍",
                  "오":"🐴","미":"🐑","신":"🐒","유":"🐓","술":"🐕","해":"🐗"}
    zodiac = content.get("zodiac_sign", "자")
    draw.text((W // 2, H // 2 - 230), zodiac_map.get(zodiac, "⭐"),
              fill=(255, 255, 255), font=font_xl, anchor="mm")

    # ─ 훅 텍스트 (중앙) ─────────────────────────
    hook = content.get("hook", "오늘의 운세")
    draw.text((W // 2, H // 2 - 80), hook, fill=(255, 248, 220), font=font_lg, anchor="mm")

    # ─ 행운 요소 배지 ────────────────────────────
    lucky = content.get("lucky_element", "")
    if lucky:
        badge_w = 320
        bx1, by1 = W//2 - badge_w//2, H//2 - 18
        bx2, by2 = W//2 + badge_w//2, H//2 + 22
        draw.rounded_rectangle([bx1, by1, bx2, by2], radius=12,
                                fill=(*accent, 40), outline=(*accent, 120), width=1)
        draw.text((W // 2, H // 2 + 2), f"✨ {lucky[:20]}", fill=(*accent, 255), font=font_sm, anchor="mm")

    # ─ 본문 텍스트 ───────────────────────────────
    main = content.get("main_text", "")
    lines = [l.strip() for l in main.split("\n") if l.strip()][:4]
    for i, line in enumerate(lines):
        draw.text((W // 2, H // 2 + 80 + i * 52), line,
                  fill=(210, 210, 235), font=font_md, anchor="mm")

    # ─ CTA 버튼 ──────────────────────────────────
    cta = content.get("cta", "💬 무료 카카오 상담")
    cta_y = H - 155
    btn_w = 460
    draw.rounded_rectangle([W//2 - btn_w//2, cta_y - 32, W//2 + btn_w//2, cta_y + 32],
                            radius=28, fill=accent)
    draw.text((W // 2, cta_y), cta, fill=(20, 10, 0), font=font_md, anchor="mm")

    # ─ 하단 URL ──────────────────────────────────
    draw.text((W // 2, H - 65), FORM_URL, fill=(120, 120, 150), font=font_sm, anchor="mm")

    out_path = OUT_DIR / f"card_sq_{TODAY_STR}.jpg"
    base.convert("RGB").save(str(out_path), "JPEG", quality=94)
    return out_path


def make_vertical_slides(content: dict, account: dict) -> list:
    """9:16 슬라이드 5장 생성 (Instagram/TikTok 캐러셀)"""
    W, H = 1080, 1920
    bg = hex_to_rgb(account["bg"])
    accent = hex_to_rgb(account["accent"])
    font_xl, font_lg, font_md, font_sm = get_fonts((100, 70, 44, 32))
    slide_texts = content.get("slide_texts", [])
    main_lines = [l.strip() for l in content.get("main_text", "").split("\n") if l.strip()]

    default_slides = [
        content.get("hook", "오늘의 운세"),
        main_lines[0] if len(main_lines) > 0 else "오늘의 에너지",
        main_lines[1] if len(main_lines) > 1 else "행운 요소",
        content.get("lucky_element", "행운이 함께해요"),
        content.get("cta", "무료 상담 바로가기"),
    ]
    for i, t in enumerate(default_slides):
        if i < len(slide_texts) and slide_texts[i]:
            default_slides[i] = slide_texts[i]

    paths = []
    zodiac_map = {"자":"🐭","축":"🐂","인":"🐯","묘":"🐰","진":"🐲","사":"🐍",
                  "오":"🐴","미":"🐑","신":"🐒","유":"🐓","술":"🐕","해":"🐗"}
    zodiac_emoji = "🛍️" if account.get("channel_type") == "shopping" else zodiac_map.get(content.get("zodiac_sign", "자"), "⭐")

    for idx, slide_text in enumerate(default_slides):
        base = Image.new("RGBA", (W, H), (*bg, 255))
        glow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow_layer)

        # 바텀 글로우
        draw_radial_glow(gd, W // 2, H - 300, 700, accent, (0, 0, 0), steps=120)
        # 탑 소글로우
        draw_radial_glow(gd, W // 2, 350, 350, accent, (0, 0, 0), steps=80)
        base = Image.alpha_composite(base, glow_layer)

        deco = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dd = ImageDraw.Draw(deco)
        draw_circle_decorations(dd, W // 2, H // 2, 480, accent, n=12)
        draw_hex_lines(dd, W // 2, H // 2, 460, accent)
        dd.ellipse([W//2 - 500, H//2 - 500, W//2 + 500, H//2 + 500],
                   outline=(*accent, 25), width=2)
        base = Image.alpha_composite(base, deco)
        draw = ImageDraw.Draw(base)

        # 상단바
        draw.rectangle([(0, 0), (W, 12)], fill=accent)
        # 페이지 번호
        draw.text((W // 2, 70), f"{idx + 1} / {len(default_slides)}",
                  fill=(*accent, 180), font=font_sm, anchor="mm")
        # 계정명
        draw.text((W // 2, 130), account["name"], fill=(*accent, 220), font=font_sm, anchor="mm")

        # 중앙 이모지
        draw.text((W // 2, H // 2 - 320), zodiac_emoji, fill=(255, 255, 255), font=font_xl, anchor="mm")

        # 슬라이드 메인 텍스트
        slide_lines = wrap_text(slide_text, 14) if len(slide_text) > 14 else [slide_text]
        for li, sl in enumerate(slide_lines[:3]):
            y = H // 2 - 80 + li * 90
            draw.text((W // 2, y), sl, fill=(255, 248, 220), font=font_lg, anchor="mm")

        # 서브텍스트 (마지막 슬라이드 = CTA 강조)
        if idx == len(default_slides) - 1:
            cta_y = H - 220
            draw.rounded_rectangle([W//2 - 380, cta_y - 48, W//2 + 380, cta_y + 48],
                                    radius=36, fill=accent)
            draw.text((W // 2, cta_y), f"💬 {content.get('cta', '무료 카카오 상담')}",
                      fill=(20, 10, 0), font=font_md, anchor="mm")
            draw.text((W // 2, H - 100), FORM_URL, fill=(120, 120, 150), font=font_sm, anchor="mm")
        else:
            # 날짜
            draw.text((W // 2, H - 120), TODAY_KR, fill=(150, 150, 180), font=font_sm, anchor="mm")

        out_path = OUT_DIR / f"slide_v_{idx + 1:02d}_{TODAY_STR}.png"
        base.convert("RGB").save(str(out_path), "PNG")
        paths.append(str(out_path))

    return paths


# ── 저장 ──────────────────────────────────────────────────────
print("이미지 카드 생성 중...")
card_path = make_image_card(content, account)

print("슬라이드 이미지 생성 중...")
slide_paths = make_vertical_slides(content, account)

print(f"✅ 카드: {card_path.name}")
print(f"✅ 슬라이드 {len(slide_paths)}장 생성 완료")

meta = {
    "date": TODAY_STR,
    "hour_kst": HOUR_KST,
    "topic": TOPIC,
    "account": account,
    "slot": time_slot,
    "content": content,
    "image_path": str(card_path),
    "image_card": str(card_path),
    "slides_vertical": slide_paths,
}

meta_path = OUT_DIR / "meta.json"
with open(meta_path, "w", encoding="utf-8") as f:
    json.dump(meta, f, ensure_ascii=False, indent=2)

# 레거시 호환
legacy_dir = Path(__file__).parent / "sns_output"
legacy_dir.mkdir(exist_ok=True)
with open(legacy_dir / "meta.json", "w", encoding="utf-8") as f:
    json.dump(meta, f, ensure_ascii=False, indent=2)

print(f"✅ meta.json 저장 완료 → {meta_path}")
