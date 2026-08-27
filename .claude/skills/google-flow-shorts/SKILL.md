# google-flow-shorts

Google Flow에 직접 붙여넣을 수 있는 쇼핑 숏츠 프롬프트 패키지를 생성하는 스킬.
Python/API 키 불필요. Claude가 인터랙티브하게 정보를 수집하고 완성된 프롬프트를 즉시 출력한다.

---

## 실행 방식

이 스킬이 로드되면 Claude는 아래 단계를 순서대로 실행한다.
**설명하지 말고 바로 실행한다.**

---

### 1. 제품 정보 수집

사용자 메시지에서 아래 정보를 추출한다. 없는 항목만 물어본다 (한 번에 모두).

| 항목 | 필수 | 예시 |
|------|------|------|
| 제품명 | ✅ | "딱딱이 복숭아", "무선 청소기 PRO" |
| 가격 | 권장 | 9900 (원) |
| 핵심 기능/USP | 권장 | "한 번 충전에 60분" |
| 훅 유형 | 선택 | 가격충격/문제공감/발견기쁨/비교반전/소리훅 |
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

### 3. 1.5초 단위 10씬 대본 생성 (한국어)

아래 구조로 한국어 대본을 생성한다. 제품명, 가격, 인물, 훅 유형에 맞게 내용을 채운다.

```
[씬1 · 0–1.5초] 오프닝 프레임
→ {인물}이/가 카메라를 정면으로 응시. {훅 감정} 표정.

[씬2 · 1.5–3초] 훅 전달
→ {훅 유형에 맞는 핵심 한 줄 대사}

[씬3 · 3–4.5초] 맥락 설정
→ {공감/배경 설명 한 문장}

[씬4 · 4.5–6초] 제품 리빌
→ {제품명}을 카메라 앞에 천천히 들어 보인다.

[씬5 · 6–7.5초] 기능 시연 1
→ {핵심 기능 USP 시연 장면 묘사}

[씬6 · 7.5–9초] 기능 시연 2
→ {두 번째 포인트 B-roll 장면}

[씬7 · 9–10.5초] 감정 비트
→ {만족/기쁨 반응 한 문장}

[씬8 · 10.5–12초] 가치 확인
→ {가격/혜택 재확인 + 확신 표정}

[씬9 · 12–13.5초] 긴박감
→ {한정/희소성 언급. 카메라 직시.}

[씬10 · 13.5–15초] CTA 마무리
→ "링크 눌러봐." + {가격} 원.
```

---

### 4. Google Flow 영문 프롬프트 생성

아래 형식으로 완성된 영문 프롬프트를 생성한다.
**이 블록이 Google Flow에 바로 붙여넣는 최종 출력이다.**

```
[SUBJECT]
{인물 영문 프리셋}

[SCENE & LOCATION]
{배경 영문 프리셋}

[CAMERA]
{카메라 영문 프리셋}

[HOOK]
{훅 영문 패턴}. Subject says: "{씬2 대사를 영어로}."

[MICRO-SCENE STRUCTURE — 10 scenes × 1.5s]
Scene 1 (0–1.5s): Opening freeze frame — {씬1 설명 영어}
Scene 2 (1.5–3s): Hook delivery — {씬2 설명 영어}
Scene 3 (3–4.5s): Context / setup — {씬3 설명 영어}
Scene 4 (4.5–6s): Product reveal — Holds product "{제품명}" clearly toward camera
Scene 5 (6–7.5s): Feature demo 1 — {씬5 설명 영어}
Scene 6 (7.5–9s): Feature demo 2 — {씬6 설명 영어}
Scene 7 (9–10.5s): Emotional beat — {씬7 설명 영어}
Scene 8 (10.5–12s): Value confirm — {씬8 설명 영어}
Scene 9 (12–13.5s): Urgency — {씬9 설명 영어}
Scene 10 (13.5–15s): CTA close — Says "Click the link now." / Price: {가격} KRW

[FORMAT]
15-second vertical short-form video, 9:16 aspect ratio, mobile-first framing

[AESTHETIC]
{분위기 스타일에 맞는 한 줄: Authentic UGC / Balanced cinematic / Dramatic Rembrandt}
```

---

### 5. 자막 (1.5초 단위 10씬)

```
[0–1.5초]  {씬1 자막 — 4단어 이내}
[1.5–3초]  {씬2 자막 — 훅 핵심 문구}
[3–4.5초]  {씬3 자막}
[4.5–6초]  {씬4 자막}
[6–7.5초]  {씬5 자막}
[7.5–9초]  {씬6 자막}
[9–10.5초] {씬7 자막}
[10.5–12초]{씬8 자막}
[12–13.5초]{씬9 자막}
[13.5–15초]{씬10 자막 — CTA}
```

**자막 스타일 (CapCut 설정)**
- 글씨체: 고딕 Bold / 굵기: 초굵게 / 그림자: ON
- 훅 구간(씬1-2): 주황색 강조 / CTA 구간(씬9-10): 보라색 강조

---

### 6. 음성 추천 (CapCut TTS)

제품·훅 유형에 맞는 목소리를 추천한다:
- 가격충격 / 비교반전 → **준서** (30대 남성·에너지) 또는 **미나** (20대 여성·활기참)
- 문제공감 → **소연** (30대 여성·차분) 또는 **민준** (30대 남성·차분)
- 발견기쁨 → **은지** (20대 여성·즐거움) 또는 **준서** (20대 남성·활기)
- 소리훅 → **ASMR 모드** 또는 **태양** (30대 남성·에너지)

---

### 7. 배경음악 & 해시태그

**BGM 제안**: 훅 유형에 맞는 BPM/장르 한 줄
**해시태그**: 제품명 관련 2개 + 기본 10개 포함, 총 12개 이상

```
#쇼핑 #할인 #가성비 #추천 #숏츠 #틱톡 #인스타 #구매 #리뷰 #언박싱
```

---

### 8. 출력 완료 후 한 줄

"다른 훅 유형 버전도 만들까요?" 또는 "TopView용 버전도 생성할까요?"

---

## 출력 형식 규칙

- 각 섹션을 `---` 구분선으로 분리한다
- Google Flow 프롬프트 블록은 코드 블록(```)으로 감싼다
- 한국어 대본과 영문 프롬프트를 모두 출력한다
- 길어도 생략하지 않는다 (모든 10씬을 완성한다)
- 설명/주석 없이 결과물만 깔끔하게 출력한다
