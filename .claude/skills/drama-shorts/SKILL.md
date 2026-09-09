# /drama-shorts — 드라마쇼츠 60초 스크립트 생성기

유튜브 쇼츠 막장 드라마 콘텐츠를 즉시 생성한다.
MagicLight.AI에 바로 붙여넣기 할 수 있는 영어 완성본으로 출력한다.

## 트리거

`/drama-shorts` — 새 에피소드 생성 (채널 랜덤 또는 지정)
`/drama-shorts 드라마한방` — 드라마한방 채널 스타일로 생성
`/drama-shorts 충격실화쇼츠` — 충격실화쇼츠 채널 스타일로 생성
`/drama-shorts EP.5` — 에피소드 번호 지정

## 채널별 스타일 규칙

### 드라마한방
- 타겟: 30–60대
- 소재: 시어머니/며느리, 가족 갈등, 재산 분쟁
- 톤: 감동형 + 권선징악. 결말은 반드시 권선징악.
- 클릭코드: 정보격차형("알고보니"), 감정자극형(분노→통쾌함)

### 충격실화쇼츠
- 타겟: 20–40대
- 소재: 불륜, 배신, 반전 폭로, 숨겨진 비밀
- 톤: 막장 + 충격 반전. 마지막에 예상 못 한 반전 필수.
- 클릭코드: 반전예고형("결말을 봐라"), 숫자/금액 포함 자극형

## 출력 형식 — 무조건 이 순서로

생성할 때 반드시 아래 순서와 형식을 지킨다.
**모든 스크립트 본문은 영어로.** 섹션 라벨만 한국어.

---

### 제목 5개 (A/B 테스트용)
각 제목에 클릭코드 유형 표시:
- 정보격차형: "알고보니 / The truth about / What nobody knew"
- 반전예고형: "결말이 충격 / The ending destroys everything / What happened next"
- 감정자극형: 분노·공감·통쾌함 유발 표현
- 숫자/금액 포함: 구체적 금액, 기간, 횟수
- 질문형: "Who is...? / Why did she...?"

---

### STEP 1 — Video Style Prompt
한 문단 영어. 아래 요소 반드시 포함:
- "Korean drama short, realistic cinematic style, 9:16 vertical format"
- 배경 (apartment / office / parking lot 등 장면에 맞게)
- 조명 (night / dramatic low-key / dim hallway 등)
- "close-up facial expressions, subtitles on screen, tense [장르] music"
- "ultra-realistic, 4K"

---

### STEP 2 — Full Narration Script (60 seconds)

4개 블록으로 구성. 각 블록에 시간 명시.

**[HOOK — 0 to 5 seconds]**
시청자를 멈추게 하는 첫 문장. 충격적 상황 직접 언급. 1–2문장.
Screen direction: 가장 자극적인 시각 요소 묘사.

**[DEVELOPMENT — 6 to 45 seconds]**
갈등 전개. 구체적인 대화(NARRATOR/CHARACTER NAME 표기)와 장면 지시.
Screen directions는 이탤릭으로 괄호 안에.
긴장감 점층: 사실 하나 → 의심 → 확인 → 충격 고조.

**[CLIMAX — 46 to 55 seconds]**
반전 or 클라이막스. 예상 못 한 반전 필수.
ON SCREEN TEXT: 굵은 글씨로 핵심 충격 한 줄.

**[ENDING HOOK — 56 to 60 seconds]**
다음 에피소드 유도. "Episode 2" 또는 "Part 2" 언급.
FINAL TEXT: 팔로우 유도 문장.

---

### STEP 3 — Thumbnail Image Prompt
한 문단 영어. 반드시 포함:
- 주인공 묘사 (나이, 성별, 감정 상태)
- 배경/조명 묘사
- "Cinematic color grade" + 색감 방향 (teal-orange / cold blue / warm amber 등)
- "Vertical 9:16 format, ultra-realistic 8K"
- "Bold Korean text overlay space at top and bottom of frame"

---

### STEP 4 — Hashtags
한국어 + 영어 혼합 13개.
반드시 포함: #드라마쇼츠 #충격실화쇼츠 또는 #드라마한방 #YouTubeShorts #KoreanDramaShorts

---

## 출력 후 마지막에 항상 이걸 추가

```
---
다음 단계:
• MagicLight.AI → 위 순서대로 STEP 1~4 붙여넣기
• EP.[다음번호] 스크립트 → /drama-shorts 입력
• 썸네일 → 썸네일 메이커에서 STEP 3 프롬프트 사용
```

## 품질 기준

- 훅(0–5초)은 반드시 충격적인 상황으로 시작. "오늘 날씨" 같은 평범한 도입부 금지.
- 반전은 실제로 예상 못 하는 것이어야 함. 뻔한 반전 금지.
- 대사는 자연스러운 구어체 영어. 번역투 금지.
- 장면 지시는 구체적으로 (표정, 조명, 소리 포함).
- 에피소드마다 소재가 겹치지 않게 — 채널별 소재 목록에서 골고루.
