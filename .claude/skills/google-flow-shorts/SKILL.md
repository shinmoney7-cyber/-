# google-flow-shorts

Google Flow에 직접 붙여넣을 수 있는 쇼핑 숏츠 프롬프트 패키지를 생성하는 스킬.
Python/API 키 불필요. Claude가 인터랙티브하게 정보를 수집하고 완성된 프롬프트를 즉시 출력한다.

> **언어 규칙 (최우선)**: 자막과 음성 언어는 사용자가 선택한다.
> 지원 언어: **한국어 / English / 日本語 / 中文**
> 사용자가 지정하지 않으면 **한국어**를 기본값으로 사용한다.
> 대본·자막·음성 대사는 선택된 언어로 작성한다. Google Flow 영문 프롬프트 안에도 해당 언어 대사를 그대로 넣는다.

---

## 실행 방식

이 스킬이 로드되면 Claude는 아래 단계를 순서대로 실행한다.
**설명하지 말고 바로 실행한다.**

---

### 1. 제품 정보 수집

사용자 메시지에서 아래 정보를 추출한다. 없는 항목만 물어본다 (한 번에 모두).

| 항목 | 필수 | 예시 |
|------|------|------|
| 언어 | 선택 | 한국어(기본) / English / 日本語 / 中文 |
| 제품명 | ✅ | "딱딱이 복숭아", "무선 청소기 PRO" |
| 가격 | 권장 | 9900 (원) |
| 핵심 기능/USP | 권장 | "한 번 충전에 60분" |
| 훅 유형 | 선택 | 가격충격/문제공감/발견기쁨/비교반전/소리훅 |
| CTA 유형 | 선택 | 링크클릭/한정수량/가격강조/팔로우할인/댓글참여/저장하기 |
| 인물 | 선택 | 30대 여성 / 40대 남성 / 20대 여성 / 20대 남성 |
| 배경 | 선택 | 야간 차량 / 낮 카페 / 홈 / 도심 거리 |

정보가 부족하면 Claude가 제품 카테고리에 맞는 최선의 선택을 적용한다.

---

### 2. 파라미터 확정

아래 매핑에서 Claude가 자동으로 선택한다. 사용자가 지정했으면 그것을 우선한다.

**인물 영문 프리셋**
- 30대 여성: `Korean woman in her early-to-mid 30s, natural dewy complexion, subtle contouring makeup, shoulder-length dark brown hair, warm confident presence, smart casual attire`
- 40대 남성: `Korean man in his early-to-mid 40s, genuine slightly weathered complexion, neat short hair, approachable reliable presence, neat casual attire`
- 20대 여성: `Korean woman in her early-to-mid 20s, bright youthful complexion, minimalist natural makeup, trendy casual streetwear, expressive energetic presence`
- 20대 남성: `Korean man in his mid-to-late 20s, clean clear complexion, neatly styled dark hair, confident modern streetwear`

**배경 영문 프리셋**
- 야간 차량: `interior of moving car at night, bokeh city lights visible through windows`
- 낮 카페: `sunlit modern café interior, warm natural light, soft background blur`
- 홈: `clean minimalist home interior, comfortable ambient lighting`
- 도심 거리: `busy urban sidewalk, outdoor natural light, slight depth-of-field blur`

**카메라 영문 프리셋** (훅 유형별 자동 선택)
- 가격충격/비교반전: `static locked-off camera, direct eye contact, confessional talking-head`
- 문제공감/발견기쁨: `handheld shaky movement, authentic vlog-style intimacy`
- 소리훅: `slow cinematic push-in, shallow depth of field, reveal movement`

**훅 영문 패턴**
- 💸 가격충격: `Price-shock hook: exaggerated double-take reaction, hand raised in disbelief`
- 💬 문제공감: `Problem-empathy hook: slow empathetic nod, knowing expression`
- ✨ 발견기쁨: `Discovery-joy hook: barely-contained excitement, head shake of disbelief`
- 🔄 비교반전: `Comparison-reversal hook: holds two items, dramatic reveal expression`
- 🔊 소리훅: `Sound hook: open with product's distinctive sound, camera reveals source`

---

### 2b. CTA 유형 선택 (씬9·씬10 자막 결정)

CTA 유형이 없는 항목만 Claude가 자동 선택한다. 씬9·씬10 대사는 아래 패턴에서 가져온다.

| CTA 유형 | 씬9 (12–13.5초) | 씬10 (13.5–15초) |
|---------|----------------|-----------------|
| 🔗 링크 클릭 | 지금 링크 눌러봐 | 바로 아래 링크 → 직구 가능 |
| ⏰ 한정 수량 | 수량 한정 — 오늘 놓치면 없어 | 지금 아니면 내일은 품절 |
| 💰 가격 강조 | 딱 오늘만 이 가격 | 내일은 원래 가격 — 지금 눌러봐 |
| 👥 팔로우 할인 | 팔로우하면 할인코드 DM | 지금 팔로우 → 코드 받기 |
| 💬 댓글 참여 | 갖고 싶으면 댓글에 '원해' | 댓글 확인하고 바로 DM 드릴게 |
| 🔖 저장하기 | 나중에 사려면 지금 저장 | 저장 → 생각날 때 눌러봐 |

영어·일본어·중국어를 선택한 경우 해당 언어 등가 표현으로 자동 대체한다.

---

### 3. 대본 생성 (1.5초 단위 10씬) — 선택된 언어로

**모든 대사·자막은 선택된 언어(한국어/영어/일본어/중국어)**로 생성한다. 제품명·가격·인물·훅 유형에 맞게 채운다.

```
[씬1 · 0–1.5초] 오프닝 프레임
→ (한국어 행동 묘사 — 대사 없이 표정/행동으로 시선 고정)

[씬2 · 1.5–3초] 훅 전달 ★한국어 대사
→ "{한국어 핵심 훅 한 줄, 5단어 이내}"

[씬3 · 3–4.5초] 맥락 설정 ★한국어 대사
→ "{공감/배경 설명 한 문장}"

[씬4 · 4.5–6초] 제품 리빌
→ {제품명}을 카메라 앞에 천천히 들어 보인다.

[씬5 · 6–7.5초] 기능 시연 1 ★한국어 대사
→ "{핵심 기능 USP 한 문장}"

[씬6 · 7.5–9초] 기능 시연 2 ★한국어 대사
→ "{두 번째 포인트 한 문장}"

[씬7 · 9–10.5초] 감정 비트 ★한국어 대사
→ "{만족/기쁨 한 문장}"

[씬8 · 10.5–12초] 가치 확인 ★한국어 대사
→ "{가격/혜택 재확인 한 문장}"

[씬9 · 12–13.5초] 긴박감 ★한국어 대사
→ "{한정/희소성 한 문장. 카메라 직시.}"

[씬10 · 13.5–15초] CTA 마무리 ★한국어 대사
→ "링크 눌러봐." + {가격}원
```

---

### 4. Google Flow 영문 프롬프트 생성

아래 형식으로 완성된 영문 프롬프트를 생성한다.
**이 블록이 Google Flow에 바로 붙여넣는 최종 출력이다.**
대사(Subject says)는 **한국어 그대로** 넣는다 — 영어로 번역하지 않는다.

```
[SUBJECT]
{인물 영문 프리셋}

[SCENE & LOCATION]
{배경 영문 프리셋}

[CAMERA]
{카메라 영문 프리셋}

[LANGUAGE]
Subject speaks Korean throughout. All spoken dialogue and on-screen text in Korean (한국어). Do not use English dialogue.

[HOOK]
{훅 영문 패턴}. Subject says in Korean: "{씬2 한국어 대사 그대로}."

[MICRO-SCENE STRUCTURE — 10 scenes × 1.5s, all dialogue in Korean]
Scene 1 (0–1.5s): Opening — {씬1 행동 영어 묘사}, no dialogue
Scene 2 (1.5–3s): Hook — Subject says in Korean: "{씬2 한국어 대사}"
Scene 3 (3–4.5s): Context — Subject says in Korean: "{씬3 한국어 대사}"
Scene 4 (4.5–6s): Product reveal — holds "{제품명}" up to camera
Scene 5 (6–7.5s): Feature demo 1 — Subject says in Korean: "{씬5 한국어 대사}"
Scene 6 (7.5–9s): Feature demo 2 — Subject says in Korean: "{씬6 한국어 대사}"
Scene 7 (9–10.5s): Emotional beat — Subject says in Korean: "{씬7 한국어 대사}"
Scene 8 (10.5–12s): Value confirm — Subject says in Korean: "{씬8 한국어 대사}"
Scene 9 (12–13.5s): Urgency — Subject says in Korean: "{씬9 한국어 대사}"
Scene 10 (13.5–15s): CTA — Subject says in Korean: "링크 눌러봐." Price: {가격}원

[FORMAT]
15-second vertical short-form video, 9:16 aspect ratio, mobile-first framing

[AESTHETIC]
{분위기: Authentic UGC / Balanced cinematic / Dramatic Rembrandt}
```

---

### 5. 한국어 자막 (1.5초 단위 10씬)

**모든 자막은 한국어**로 작성한다. 씬당 최대 10자 이내로 짧고 강하게.

```
[0–1.5초]   {한국어 자막 — 표정/행동 묘사, 4자 이내}
[1.5–3초]   {한국어 훅 핵심 문구}
[3–4.5초]   {한국어 맥락 자막}
[4.5–6초]   {한국어 제품 자막}
[6–7.5초]   {한국어 기능 자막}
[7.5–9초]   {한국어 기능2 자막}
[9–10.5초]  {한국어 감정 자막}
[10.5–12초] {한국어 가치 자막}
[12–13.5초] {한국어 긴박감 자막}
[13.5–15초] {한국어 CTA 자막}
```

**CapCut 자막 스타일 설정**
- 글씨체: 고딕 Bold (한국어 지원 폰트 필수)
- 굵기: 초굵게 / 그림자: ON / 테두리: 흰색 2px
- 훅 구간(씬1-2): 주황색 `#FF7C3C` 강조
- 메인 구간(씬3-8): 흰색
- CTA 구간(씬9-10): 보라색 `#9B59F5` 강조

---

### 6. 음성 선택 (CapCut TTS — 선택된 언어)

CapCut > 텍스트 음성 변환 > **언어 선택** 후 아래 목소리 사용.

훅 유형별 추천 목소리 (언어에 맞게 해당 열 사용):

| 훅 유형 | 🇰🇷 한국어 | 🇺🇸 English | 🇯🇵 日本語 | 🇨🇳 中文 |
|---------|-----------|------------|----------|--------|
| 💸 가격충격 | 미나·준서 | Olivia·Oliver | さくら·だいき | 小云·大壮 |
| 💬 문제공감 | 소연·민준 | Ava·William | みさき·りょう | 小雪·云扬 |
| ✨ 발견기쁨 | 은지·준서 | Mia·James | ことね·けんじ | 小倩·小明 |
| 🔄 비교반전 | 태양·지영 | Oliver·Isabella | だいき·まなみ | 大壮·晓萱 |
| 🔊 소리훅 | ASMR 모드 | ASMR | ASMRモード | ASMR模式 |

> CapCut TTS: 텍스트 추가 → 텍스트 음성 변환 → **언어 선택** → 목소리 선택 → 씬별 대사 입력

---

### 7. 배경음악 & 해시태그

**BGM 제안**: 훅 유형에 맞는 BPM/장르 한 줄
**해시태그**: 선택된 언어에 맞는 태그 12개 이상

- 🇰🇷: `#{제품명} #{제품명}추천 #쇼핑 #할인 #가성비 #추천 #숏츠 #틱톡 #인스타 #구매 #리뷰 #언박싱`
- 🇺🇸: `#deal #discount #viral #shorts #TikTok #unboxing #review #musthave #trending #sale`
- 🇯🇵: `#お得 #ショッピング #おすすめ #ショート動画 #TikTok #レビュー #購入 #格安 #バズり`
- 🇨🇳: `#购物 #折扣 #好物 #短视频 #抖音 #开箱 #测评 #必买 #优惠 #好价`

---

### 8. 출력 완료 후 한 줄

"다른 훅 유형 버전도 만들까요?" 또는 "TopView용 버전도 생성할까요?"

---

## 저작권·원본성 원칙

> **TikTok·Instagram·YouTube 영상은 스타일 참고 자료일 뿐이다.**
> 기존 플랫폼 영상을 그대로 복사·재업로드하는 것은 절대 금지한다.
> Google Flow로 생성되는 영상은 **100% 고유한 AI 생성 원본** 이어야 한다.
> 인물·씬·대사 모두 새로 생성된 콘텐츠로 구성한다.

---

## 출력 형식 규칙

- **자막과 음성 대사는 선택된 언어(한국어/영어/일본어/중국어)로 작성** — 미지정 시 한국어 기본
- Google Flow 프롬프트 안 대사도 선택된 언어 원문 그대로 삽입 (다른 언어로 번역 금지)
- 각 섹션을 `---` 구분선으로 분리
- Google Flow 프롬프트 블록은 코드 블록(```)으로 감쌈
- 한국어 대본 + 영문 프롬프트(한국어 대사 포함) + 한국어 자막 모두 출력
- 모든 10씬을 생략 없이 완성
- 설명/주석 없이 결과물만 깔끔하게 출력
