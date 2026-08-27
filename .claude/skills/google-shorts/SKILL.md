# google-shorts

구글 쇼핑 검색 → Gemini 대본/자막/해시태그/BGM → TopView 패키지를
**CLI 한 줄**로 처리하는 스킬. GOOGLE_API_KEY 하나로 전부 동작.

## 트리거

- "구글 플로우", "구글 쇼핑쇼츠", "google shorts"
- "대본 만들어", "자막 생성", "숏츠 패키지"
- 상품명 + (구글 | 쇼츠 | topview | 대본 | 자막) 조합

## 필요 환경변수 (2개뿐)

```
GOOGLE_API_KEY=...   # Custom Search + Gemini 공용
GOOGLE_CX=...        # Programmable Search Engine ID
```

## 사용 방법

### 기본 실행 (테스트 — API 키 없이)

```bash
python -m shopping_shorts_sync google-shorts run -k "선크림"
```

### 실제 실행 (Google + Gemini API 호출)

```bash
python -m shopping_shorts_sync google-shorts run -k "선크림 SPF50" --live
```

### 옵션 전체

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `-k / --keyword` | 필수 | 구글 쇼핑 검색어 |
| `--limit` | 5 | 검색 결과 최대 개수 |
| `--index` | 0 | 사용할 결과 인덱스 |
| `--dry-run / --live` | dry-run | dry: 모의 데이터 / live: 실제 API |
| `--no-coupang` | off | 쿠팡 매칭 건너뛰기 |
| `--model` | gemini-2.0-flash | Gemini 모델 변경 |
| `--json-out` | off | TopView 패키지를 JSON으로 출력 |

### 검색 결과만 먼저 확인

```bash
python -m shopping_shorts_sync google-shorts search -k "선크림" --live
```
→ 결과 목록 확인 후 `--index 2` 처럼 원하는 상품 번호 지정

### JSON 출력 (TopView 붙여넣기용)

```bash
python -m shopping_shorts_sync google-shorts run -k "선크림" --live --json-out
```

## 출력 예시

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎬  무선 청소기 PRO  쇼핑쇼츠 패키지
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

▶ 대본 (15초)
  [0-3초]  자막: "이거 실화임?"
            화면: 먼지 앞에 청소기 등장
  [3-12초] 자막: "흡입력 25,000Pa / 배터리 60분"
            화면: 카펫·소파·틈새 청소 연속 전환
  [12-15초] 자막: "지금 59,000원"
             화면: 링크 클릭 유도 손 제스처

▶ 자막 목록
  1. 이거 실화임?
  2. 흡입력 25,000Pa / 배터리 60분
  3. 지금 59,000원

▶ 배경음악
  경쾌한 비트 BPM 120, 팝 분위기

▶ 해시태그
  #무선청소기  #청소기추천  #쇼핑  #할인  #가성비
  #홈리빙  #청소  #생활가전  #숏츠  #쿠팡

▶ TopView 입력 정보
  이미지 URL : https://...
  제품 URL   : https://link.coupang.com/...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Claude에게 요청하는 방법

사용자가 "구글 플로우로 선크림 대본 만들어줘" 라고 하면:

1. 키워드를 파악한다 (`선크림`)
2. `google-shorts search` 로 결과 목록을 먼저 보여준다
3. 사용자가 원하는 인덱스를 확인하거나 0번으로 진행한다
4. `google-shorts run -k "선크림" --live` 를 실행해 전체 패키지를 출력한다
5. 결과를 보여주고 "Inpock에 등록할까요?" 를 제안한다

## 참조 파일

- `src/shopping_shorts_sync/cli.py` — `google_shorts_group` 커맨드 그룹
- `src/shopping_shorts_sync/search/google.py` — GoogleShopClient
- `src/shopping_shorts_sync/topview_gpt.py` — generate_script (Gemini)
