# google-shorts

**GOOGLE_API_KEY 하나로** 구글 쇼핑 검색 + Gemini 대본/자막/해시태그/BGM 생성 + TopView 패키지까지 모두 처리하는 스킬.
OpenAI 등 외부 서비스 불필요 — Google만 사용.

## 트리거

- "구글 플로우", "구글 쇼핑쇼츠", "google shorts"
- "대본 만들어", "자막 생성", "숏츠 패키지"
- 상품명 + (구글 | 쇼츠 | topview | 대본 | 자막) 조합

## 필요 환경변수 (2개뿐)

```
GOOGLE_API_KEY=...   # Custom Search + Gemini 공용 키
GOOGLE_CX=...        # Programmable Search Engine ID
```

## 실행 절차

### 1단계 — 상품 정보 확인

사용자가 제공한 정보를 파악한다. 없는 항목은 질문한다:
- **키워드** (필수): 구글 쇼핑 검색어
- **가격** (선택): 없으면 "가격 미정" 처리

### 2단계 — 구글 쇼핑 검색

```python
from shopping_shorts_sync.config import load_config
from shopping_shorts_sync.search.orchestrator import search_one_source

config = load_config()
hits = search_one_source("google", "<키워드>", config, dry_run=False, limit=5)
top = hits[0]  # 상위 1개 선택 (여러 개면 사용자에게 선택지 제시)
```

### 3단계 — Gemini로 전체 패키지 생성

`generate_script()`를 호출한다. 내부적으로 `gemini-2.0-flash`를 사용하며,
**같은 GOOGLE_API_KEY**로 호출된다.

```python
from shopping_shorts_sync.topview_gpt import generate_script

result = generate_script(
    product_name=top.name,
    product_url=top.product_url,   # 또는 쿠팡 딥링크
    image_url=top.image_url,
    price=top.price,
    # model="gemini-2.0-flash"  # 기본값
)
```

**생성되는 항목**

| 필드 | 내용 |
|------|------|
| `result.script` | 씬별 구조화 대본 (scene1/2/3 딕셔너리) |
| `result.subtitles` | 씬별 자막 텍스트 리스트 |
| `result.bgm` | 배경음악 분위기 설명 |
| `result.hashtags` | 해시태그 10개 이상 |
| `result.topview_payload` | TopView 입력용 전체 패키지 |

### 4단계 — 결과 출력

```
## 🎬 [상품명] 쇼핑쇼츠 패키지

### 대본
[0-3초] 화면: ... | 자막: "..."
[3-12초] 화면: ... | 자막: "..."
[12-15초] 화면: ... | 자막: "..." | CTA: ...

### 자막
- "..."
- "..."
- "..."

### 배경음악
...

### 해시태그
#... #... #...

### TopView 패키지 (복붙용)
product_name: ...
product_url: ...
image_url: ...
subtitles: [...]
duration_seconds: 15
```

### 5단계 — 선택적 후속 작업

- "다른 제품도 만들까요?"
- "Inpock에 이 카드를 자동 등록할까요?"
- "더 정교한 대본을 원하면 model='gemini-1.5-pro'로 재생성할까요?"

## 오류 처리

| 상황 | 대응 |
|------|------|
| GOOGLE_API_KEY 없음 | "`.env`에 GOOGLE_API_KEY와 GOOGLE_CX를 추가하세요 — 한 키로 검색과 AI 생성 모두 됩니다" |
| 검색 결과 없음 | 다른 키워드 제안 |
| Gemini 호출 실패 | 에러 메시지 출력 후 재시도 여부 물어봄 |

## 참조 모듈

- `src/shopping_shorts_sync/search/google.py` — GoogleShopClient
- `src/shopping_shorts_sync/search/orchestrator.py` — search_one_source
- `src/shopping_shorts_sync/topview_gpt.py` — generate_script (Gemini 기반)
- `src/shopping_shorts_sync/config.py` — load_config
