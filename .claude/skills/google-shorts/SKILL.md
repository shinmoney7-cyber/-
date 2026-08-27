# google-shorts

구글 쇼핑 검색으로 상품을 찾고, GPT로 15초 대본·자막·해시태그를 생성하여 TopView 입력 패키지까지 한 번에 만드는 스킬.

## 트리거

다음 중 하나가 포함되면 이 스킬을 사용한다:
- "구글 쇼핑쇼츠", "구글 플로우", "google shorts", "google 쇼핑"
- "대본 만들어", "자막 생성", "숏츠 패키지"
- 상품명 + (구글 | 쇼츠 | topview | 대본) 조합

## 실행 절차

### 1단계 — 상품 정보 확인

사용자가 제공한 정보를 파악한다. 없는 항목은 물어본다:
- **키워드** (필수): 구글 쇼핑 검색어
- **가격** (선택): 없으면 "가격 미정"으로 처리
- **카테고리** (선택): 없으면 GPT가 추론

### 2단계 — 구글 쇼핑 검색 (dry_run 가능)

```python
from shopping_shorts_sync.config import load_config
from shopping_shorts_sync.search.orchestrator import search_one_source

config = load_config()
hits = search_one_source("google", "<키워드>", config, dry_run=False, limit=5)
```

검색 결과 상위 1개를 선택한다. 여러 개면 사용자에게 선택지를 보여준다.

### 3단계 — GPT 패키지 생성

`topview_gpt.generate_script()`를 호출해 아래 항목을 모두 생성한다:

**생성 항목**
| 항목 | 내용 |
|------|------|
| 15초 대본 | [0-3초] 후킹 / [3-12초] 제품 포인트 / [12-15초] CTA |
| 자막 텍스트 | 씬별 자막 (3개 이상) |
| 배경음악 | 분위기 설명 (예: "경쾌한 비트 BPM 120") |
| 해시태그 | 플랫폼별 10개 이상 |
| TopView 패키지 | product_name, product_url, image_url, script, duration_seconds |

GPT에게 전달할 시스템 프롬프트는 `topview_gpt.py`의 `_SYSTEM_PROMPT`에 정의되어 있다.
필요시 사용자 요청에 따라 모델을 gpt-4o로 변경할 수 있다 (`model="gpt-4o"`).

### 4단계 — 결과 출력

다음 형식으로 결과를 출력한다:

```
## 🎬 [상품명] 쇼핑쇼츠 패키지

### 대본 (15초)
[0-3초] ...
[3-12초] ...
[12-15초] ...

### 자막
- 씬1: "..."
- 씬2: "..."
- 씬3: "..."

### 배경음악
...

### 해시태그
#쇼핑 #할인 ...

### TopView 입력 패키지
product_name: ...
product_url: ...
image_url: ...
script: ... (전체 대본)
duration_seconds: 15
```

### 5단계 — 선택적 후속 작업

결과 출력 후 사용자에게 제안한다:
- "다른 제품도 생성할까요?"
- "GPT-4o로 더 정교하게 만들까요?"
- "Inpock에 이 카드를 자동으로 등록할까요?"

## 오류 처리

| 상황 | 대응 |
|------|------|
| GOOGLE_API_KEY 없음 | "`.env`에 GOOGLE_API_KEY와 GOOGLE_CX를 추가하세요" |
| OPENAI_API_KEY 없음 | "`.env`에 OPENAI_API_KEY를 추가하세요" |
| 검색 결과 없음 | 다른 키워드를 제안하거나 네이버 검색으로 fallback |
| GPT 호출 실패 | 에러 메시지 출력 후 재시도 여부 물어봄 |

## 환경변수

```
GOOGLE_API_KEY=...   # Google Custom Search API 키
GOOGLE_CX=...        # Programmable Search Engine ID
OPENAI_API_KEY=...   # OpenAI API 키
```

## 참조 모듈

- `src/shopping_shorts_sync/search/google.py` — GoogleShopClient
- `src/shopping_shorts_sync/search/orchestrator.py` — search_one_source
- `src/shopping_shorts_sync/topview_gpt.py` — generate_script, TopviewScript
- `src/shopping_shorts_sync/config.py` — load_config (env 로드)
