---
name: sync-shopshorts-higgs
description: 쇼핑 숏츠 전체 제작 워크플로우 — 상품 탐색(Naver/다이소/올리브영 검색 → 쿠팡 자동매칭)부터 AIDA 대본 5개 작성·선택, Higgsfield 마케팅 영상 생성, 인포크 링크 카드 동기화까지 한 번에 처리하는 한국인 전용 스킬. shopping-shorts-sync CLI 도구와 Higgsfield MCP를 함께 사용한다. 트리거 - "쇼핑 숏츠", "상품 숏츠", "마케팅 숏츠", "대본 써줘", "상품 검색", "상품 추가", "인포크 연동", "딥링크", "AIDA", "힉스필드", shopping-shorts-sync CLI 관련 모든 작업, 상품 URL/키워드 + 숏츠/영상/인포크 조합.
---

# 쇼핑 숏츠 전체 워크플로우

> **한국인 전용.** 모든 대화·대본·자막은 한국어. 영상 등장인물은 한국인(생성 프롬프트에 `Korean man/woman` + 나이대 명시).

## 사용 도구

- **CLI** — `python -m shopping_shorts_sync <cmd>` (상품 검색·대본·딥링크·인포크 동기화)
- **Higgsfield MCP** — `mcp__*__show_marketing_studio`, `mcp__*__show_marketing_studio_generations`, `mcp__*__generate_video`
  - deferred 상태면 ToolSearch로 먼저 로드한다.

## 진입 시나리오

대화 맥락에 따라 해당 Phase부터 시작한다.

| 상황 | 시작 Phase |
|------|-----------|
| 새 상품 키워드로 검색부터 | Phase 1 |
| 쿠팡 URL 있음, 대본 필요 | Phase 2 |
| 상품·대본 준비됨, 영상만 | Phase 3 |
| 영상 완성, 인포크 동기화만 | Phase 5 |

---

## Phase 1. 상품 발굴 (검색 → 쿠팡 매칭)

Naver 쇼핑·다이소몰·올리브영에서 키워드로 검색 후 쿠팡 상품과 자동매칭해 `products.json`에 추가한다.

### 1-a. 검색

```bash
python -m shopping_shorts_sync search run \
  --keyword "<키워드>" \
  --limit 5 \
  --dry-run   # 실전: --live (CALIBRATION.md 선행 필수)
```

결과(소스별 목록)를 정리해 보여주고 어떤 소스의 몇 번 상품을 쓸지 고른다.

### 1-b. 쿠팡 자동매칭 + products.json 등록

```bash
python -m shopping_shorts_sync search match \
  --keyword "<1-a와 같은 키워드>" \
  --source <naver|daiso|oliveyoung> \
  --index <선택 번호> \
  --target-page <harujin|shinjh> \
  --category "<카테고리>" \
  --input data/products.json \
  --dry-run
```

출력에서 매칭된 쿠팡 URL과 `product_id`를 확인하고 사용자에게 알린다. 이 id가 이후 모든 Phase에서 사용된다.

> **주의**: 다이소·올리브영 RPA와 쿠팡 이름-매칭은 이름 유사도 기반이라 가끔 엉뚱한 상품이 걸릴 수 있다. 결과를 반드시 사용자와 확인한다.

---

## Phase 2. AIDA 대본 5개 작성 + 선택

상품마다 `data/scripts/<product_id>.json`에 정확히 5개의 대본 후보를 채워야 한다. **이 도구는 대본을 자동 생성하지 않는다 — Claude가 직접 작성한다.**

### 2-a. 상품 분석 + 타깃 페르소나

상품명·가격·카테고리·썸네일을 바탕으로:
- **검증된 사실**: 페이지에 명시된 스펙·가격·구성
- **금지 주장**: 후기형 멘트, 페이지에 없는 성능 주장

카테고리·가격대·이미지 톤으로 등장인물 성별·나이대를 결정한다.

| 카테고리 | 기본 페르소나 |
|---------|------------|
| 뷰티·스킨케어 | 20~30대 여성 |
| 가전·IT | 20~40대 남성 |
| 식품·건강 | 30~40대 남/여 |
| 생활·청소 | 30~40대 여성 |
| 아웃도어·스포츠 | 20~30대 남성 |

"이 상품은 [30대 한국인 여성]이 적합합니다. 근거: …" 형식으로 제시하고 확인받는다.

### 2-b. AIDA 대본 5개 작성

각 후보는 같은 구조 + **서로 다른 훅 전략**으로 작성한다. 영상 길이 기준 ~25초.

```
attention : 훅 (0~3초) — 문제 공감형 / 놀람형 / 궁금증형 / 비교형 / 숫자형 중 각각 다르게
interest  : 차별점 (3~10초) — 상품이 왜 다른지, 검증된 사실만
desire    : 사용·결과 씬 (10~20초) — 실제 사용 장면 묘사
action    : CTA (20~25초) — 링크 클릭 유도
```

작성 후 파일 내용을 보여주고 저장한다:

```json
{
  "product_id": "<product_id>",
  "candidates": [
    {"id": 1, "attention": "...", "interest": "...", "desire": "...", "action": "..."},
    {"id": 2, "attention": "...", "interest": "...", "desire": "...", "action": "..."},
    {"id": 3, "attention": "...", "interest": "...", "desire": "...", "action": "..."},
    {"id": 4, "attention": "...", "interest": "...", "desire": "...", "action": "..."},
    {"id": 5, "attention": "...", "interest": "...", "desire": "...", "action": "..."}
  ],
  "selected_id": null
}
```

저장 후 `python -m shopping_shorts_sync script show --product-id <id>` 로 정상 로드 확인.

### 2-c. 대본 선택 ⛔ 승인 게이트

5개 후보를 비교표로 보여주고 선택을 기다린다.

| # | 훅 전략 | attention 첫 줄 | 특징 |
|---|---------|---------------|------|
| 1 | 문제 공감형 | … | … |
| … | … | … | … |

선택 후:

```bash
python -m shopping_shorts_sync script select \
  --product-id <id> \
  --candidate-id <선택 번호> \
  --input data/products.json
```

선택된 대본의 `full_text`(attention → interest → desire → action 순 결합)가 이후 Higgsfield 프롬프트 작성의 기반이 된다.

---

## Phase 3. Higgsfield 씬 구조도 작성 ⛔ 승인 게이트

### 3-a. 상품 등록 (Marketing Studio)

```python
show_marketing_studio(action='fetch', type='product', url=<쿠팡 URL>)
```

스크랩된 정보를 확인하고 `media_input_id`를 확보한다.

### 3-b. 제작 개수 + 연출 방향

AskUserQuestion으로 동시 제작 개수(1~4개)와 연출 방향을 함께 묻는다. 각 선택지에 예상 크레딧 병기(1개당 약 75크레딧, `get_cost:true`로 사전 확인).

- **1개**: 단일 프리셋 선택지 3~4개 제시 (프리셋명·이 상품에 맞는 근거·예상 길이 포함)
- **여러 개**: 세트 구성으로 추천
  - 2개 → A/B 훅 테스트 (같은 페르소나, 다른 훅)
  - 3개 → 훅 다변화 (문제형·성능형·가성비형)
  - 4개 → 페르소나×템플릿 매트릭스

### 3-c. 씬 구조도 작성

Phase 2에서 선택한 대본을 AIDA 단계별로 씬에 매핑해 표로 보여준다.

| 씬 | 시간 | 화면 (비주얼) | 내레이션/대사 (한국어) | 등장인물 | 생성 방식 |
|---|---|---|---|---|---|
| S01 | 0~3초 | 훅 장면 | attention 대사 | 30대 한국인 여성 | AI 프리셋 (프리셋명) |
| S02 | 3~10초 | 차별점 장면 | interest 대사 | 동일 | AI 프리셋 |
| S03 | 10~20초 | 사용 장면 | desire 대사 | 없음 | 실제 상품 이미지 |
| S04 | 20~25초 | CTA | action 대사 | 동일 | AI 프리셋 |

작성 규칙:
- **생성 방식** 열에는 `실제 상품 이미지` / `AI 프리셋 (프리셋명)` / `AI + 상품 이미지 합성`을 구분해 기입한다.
- 핵심 성능·증거 씬은 실제 상품 이미지 기반으로 구성한다 (AI 장면으로 성능을 증명하지 않는다).

**여러 개 제작 시**: 표 앞에 세트 요약표를 먼저 보여준다.

| # | 프리셋 | 등장인물 | 훅 (첫 대사) | 길이 | 역할 |
|---|--------|---------|------------|------|------|
| 1 | This Gadget Saved Me | 20대 한국인 남성 | "이게 무슨 소리죠?" | 15초 | 문제 공감 훅 |
| 2 | Selfie Testimonial | 20대 한국인 남성 | "이 가격에 이 품질?" | 15초 | 가격 심리 훅 |

**⛔ 표 출력 후 명시적 승인 전 생성 도구 호출 금지.** 수정 시 표 갱신 후 재승인. 여러 개 제작 시 승인은 세트 전체에 대해 1회만 받는다.

---

## Phase 4. 생성 실행

승인 후에만 실행한다.

1. `generate_video` 호출 (model: `marketing_studio_video`).
   - **주의**: `url`/`type`/`mode` 파라미터는 Marketing Studio에서 무시된다.
   - 상품 이미지는 크롤링으로 확보한 `media_input_id`를 `medias: [{value, role: 'image'}]`로 전달.
   - 프리셋 스타일은 프롬프트 안에 명시 (예: `"'This Gadget Saved Me' UGC style"`).

2. 프롬프트에 반드시 포함:
   - `Korean <gender> in their <age>s` (Phase 2 페르소나) — 아바타 자동 배정에 맡기지 않는다 (외국인 배정 위험)
   - `All dialogue spoken in Korean` + 대사 원문
   - 씬 구조도의 화면 묘사, `aspect_ratio: '9:16'`

3. 길이 분기:
   - **~15초**: 1회 생성으로 완성
   - **30초 이상**: 인물 씬만 생성하고, 제품 단독 씬은 실제 상품 이미지로 CapCut 조립 안내

4. 여러 개 제작 시 병렬 제출. 제출 직후 각 job id를 기록해 사용자에게 알린다.

> **⚠️ 오류 처리**: `generate_video` 500 오류는 서버 접수됐을 수 있다. 즉시 재시도 금지 — 먼저 `show_marketing_studio_generations`로 중복 확인 후 재시도. 중복 생성은 크레딧 이중 소모.

### 4-a. 검수

1. `show_marketing_studio_generations`로 완료 확인.
2. 프레임 추출로 검증 (필수):
   ```bash
   curl -sL -o v.mp4 <rawUrl> && ffmpeg -y -loglevel error -i v.mp4 -ss 8 -frames:v 1 frame.jpg
   ```
   - 등장인물이 한국인인가? 성별·나이대가 Phase 2 페르소나와 일치하는가?
   - 깨진 한글·이상한 텍스트 오버레이가 없는가?
3. 탈락 영상은 재생성 여부를 사용자에게 묻는다. 여러 개 제작 시 영상별 판정 비교표로 정리한다.

---

## Phase 5. 딥링크 생성 + 인포크 동기화

### 5-a. 쿠팡파트너스 딥링크 생성

```bash
python -m shopping_shorts_sync deeplink generate \
  --input data/products.json \
  --dry-run   # 실전: --live (쿠팡파트너스 API 키 필요)
```

### 5-b. 인포크 링크 카드 동기화

```bash
# dry-run (브라우저 없이 시뮬레이션)
python -m shopping_shorts_sync inpock sync \
  --input data/products.json \
  --page <harujin|shinjh> \
  --dry-run

# 실전 (docs/CALIBRATION.md 선행 필수)
python -m shopping_shorts_sync inpock sync \
  --input data/products.json \
  --live --headed
```

### 5-c. 전체 파이프라인 한 번에

```bash
python -m shopping_shorts_sync sync all \
  --input data/products.json \
  --dry-run
```

### 5-d. 상태 확인·초기화

```bash
python -m shopping_shorts_sync state show
python -m shopping_shorts_sync state reset --product-id <id>   # 재처리 필요 시
```

---

## 대화 톤

- 정중한 한국어 존댓말, 간결하게.
- 각 Phase 진입 시 현재·다음 단계를 한 줄로 알린다.
- `--dry-run` 여부를 항상 명시한다. 실전 전환 시 CALIBRATION 완료 여부를 먼저 확인한다.
- 전문 용어는 쉬운 설명 병기 (예: "프리셋(미리 준비된 영상 연출 틀)").
