# 대본 템플릿 × Higgsfield 프리셋 매핑

`script-templates.md`의 5종 템플릿과 Higgsfield 마케팅 스튜디오 프리셋 카탈로그(2026-07 기준 26종)를 연결한다.
프리셋 목록은 `show_marketing_studio_v2(action='presets')`로 항상 최신을 조회해 검증한다 (카탈로그는 서버 제공 고정값이나 갱신될 수 있음).

## 1. 매핑표

| 대본 템플릿 | 1순위 프리셋 | 대안 프리셋 | 비고 |
|---|---|---|---|
| 1. 불가능한 성능 시험형 | Crush Test | Hyper Motion, Camera POV | 성능 증거 씬은 실제 영상/이미지 필수 |
| 2. 가격 충격·가성비 판정형 | Selfie Testimonial | Direct-to-Camera, Unboxing | 가격 숫자는 자막으로 크게 |
| 3. 문제 괴물 → 해결템형 | This Gadget Saved Me | Before and After, Mess to Fresh, Secret Hack Reveal | 문제 장면 → 해결 장면 대비 |
| 4. 문의 폭주·전문가 조합형 | UGC | Tutorial, Couple Sharing At Home | 허위 "문의 폭주" 연출 금지 (안전 변형 사용) |
| 5. BEST 3·5 연속 발견형 | Product Showcase | Wild Card | 상품별 클립 생성 후 조립 |

## 2. 카테고리별 프리셋 가산점

| 상품 유형 | 우선 검토 프리셋 |
|---|---|
| 패션·신발 | UGC Virtual Try On, Pro Virtual Try On, Virtual Try-On Sneakers, Unboxing Virtual Try-On |
| 뷰티 | Before and After, Selfie Testimonial |
| 식품 | Unboxing ASMR, Selfie Testimonial |
| 가전·가젯 | This Gadget Saved Me, Product Showcase, Hyper Motion |
| 프리미엄·브랜드 | TV Spot, Classic Meets Modern |
| 신기함·화제성 승부 | Giant Figure, Mystery Box, Crush Test |
| 커플·가족 타깃 | Couple Sharing At Home |

## 3. 폴백 규칙

- 필요한 연출이 어떤 프리셋에도 없으면 **Wild Card** (커스텀 아이디어 모드) 사용.
- 프리셋 slug는 presets 조회 응답의 `slug` 값을 사용한다 (예: `crush_test`, `ugc_selfie_testimonial`).
- 주의: `generate_video`에 slug를 파라미터로 넘기지 않는다 (무시됨). 프리셋 스타일은 프롬프트 문장에 명시한다.

## 4. 다중 영상 조합 전략

여러 개를 동시 제작할 때는 "같은 영상 여러 벌"이 아니라 **서로 다른 구매 심리를 1개씩 검증하는 세트**로 구성한다.

### 2개 — A/B 훅 테스트 세트
같은 페르소나·같은 템플릿, **훅(첫 2초)만 다르게**. 어떤 훅이 클릭을 만드는지 검증.

| # | 구성 | 예시 |
|---|---|---|
| A | 1순위 템플릿 × 1순위 프리셋 | 문제 훅 "이게 무슨 소리죠?" |
| B | 같은 템플릿 × 훅 변형 | 가격 훅 "방송국 마이크가 이 가격?" |

### 3개 — 훅 다변화 세트
서로 다른 구매 심리 3종을 1개씩. 상품 선택표(script-templates.md §5)의 1~3순위 템플릿을 각각 배정.

| # | 구매 심리 | 템플릿 | 프리셋 예시 |
|---|---|---|---|
| 1 | 문제 공감 | 문제 해결형 | This Gadget Saved Me |
| 2 | 성능 놀람 | 성능 시험형 | Crush Test / Hyper Motion |
| 3 | 가격 판단 | 가성비 판정형 | Selfie Testimonial |

### 4개 — 페르소나 × 템플릿 매트릭스
성별·나이대 2종 × 템플릿 2종. 타깃이 불확실한 상품에서 어느 페르소나가 반응하는지 검증.

| # | 페르소나 | 템플릿 |
|---|---|---|
| 1 | 페르소나 A (예: 20대 남성) | 1순위 템플릿 |
| 2 | 페르소나 A | 2순위 템플릿 |
| 3 | 페르소나 B (예: 30대 여성) | 1순위 템플릿 |
| 4 | 페르소나 B | 2순위 템플릿 |

### 공통 규칙
- 모든 영상은 한국인 등장 + 한국어 음성 (페르소나만 다를 수 있음).
- 크레딧: 1개당 약 75크레딧 기준으로 총액을 미리 안내하고 잔액(`balance`)을 확인한다.
- 업로드 후 조회수·클릭 데이터로 승자를 정하고, 승자 구조로 후속 영상을 만드는 사이클을 안내한다.
