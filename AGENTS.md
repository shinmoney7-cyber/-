# AGENTS.md — 청귤트립 여행쇼츠 + 쇼핑쇼츠 도구

이 저장소를 여는 AI 코딩 에이전트(OpenAI Codex, Claude Code 등)를 위한 안내입니다.
사용자는 한국어로 지시하고, 결과도 한국어로 받습니다.

## 1. 이 저장소에 있는 것
| 경로 | 내용 |
|---|---|
| `docs/travel-shorts/MASTER_PROMPT_FINAL.md` | **여행쇼츠 최종 통합 규칙** (채널·타깃·수익 등급·시즌·캘린더·로테이션·조사·대본·업로드). 여행쇼츠 작업은 항상 이 파일을 먼저 읽는다 |
| `docs/travel-shorts/CODEX.md` | Codex에서 쓰는 법, 바로 붙여 넣을 작업 지시문 |
| `docs/travel-shorts/SEASONAL_DESTINATIONS.md` · `EVERY_2_DAYS.md` · `COUPLES.md` · `POOL_STAYS.md` · `JAPAN_SERIES.md` | 여행지·시즌·캘린더 자료 |
| `docs/travel-shorts/BRAND_KIT.md` | 채널 소개 문구, 템플릿, 색 |
| `tools/grok_video.py` | 사진 → **Grok Imagine** 영상 클립 (xAI API, `XAI_API_KEY` 필요, 유료) |
| `tools/shorts_render.py` | 사진·Grok 클립 + JSON 장면 구성 → 30초 9:16 쇼츠 (자막·광고 표시·정보 카드·엔딩, 무료) |
| `src/shopping_shorts_sync/` | 쿠팡파트너스 딥링크 → 인포크 링크 카드 동기화, 상품 검색 (README.md 참고) |
| `out/` · `preview/` | 결과물 폴더 (git 제외) |

## 2. 사용자가 이렇게 말하면
- **"오늘 쇼츠 만들어줘" / "짝수일 쇼츠"** → `MASTER_PROMPT_FINAL.md` 규칙대로: 오늘 날짜로 주제 선정(캘린더 → 없으면 수익 점수 1위) → 웹 검색으로 날짜·가격·장소 확인(출처·확인일) → 결과를 `out/YYYY-MM-DD_#번호/plan.md`에 저장 → 요약을 답변으로.
- **"사진 올렸어, 영상 만들어줘"** → 아래 3번 영상 워크플로.
- **"승인"** → 영상 제작 단계로 진행하되, Grok 생성 비용(초 × 클립 수)을 먼저 알려 주고 한 번 더 확인받는다.
- **"게시해줘"** → 게시 채널과 시간을 확인받은 뒤에만. 이 저장소에는 자동 게시 기능이 없다.

## 3. 영상 워크플로 (Grok 사용)
1. 사진 7~8장을 `out/<작업폴더>/photos/`에 둔다 (직접 촬영 / 숙소 허락 / 공공누리 제1유형만).
2. 장면마다 Grok 프롬프트를 만든다 (형식은 `CODEX.md` 4번). 건물·가구·로고는 그대로, 물·김·커튼·빛·카메라만 움직이게.
3. 비용 확인 후 클립 생성:
   `python tools/grok_video.py out/<작업>/photos/01.jpg "<프롬프트>" out/<작업>/clips/01.mp4 --duration 6`
   - 처음 한 번은 `--dry-run`으로 요청 내용을 보고, xAI API 문서의 필드명과 맞는지 확인한다 (`--image-field`, `--model`, `XAI_API_BASE`로 조정).
4. `out/<작업>/spec.json`을 만든다. Grok 클립은 `{"video":"clips/01.mp4","start":0.5,"dur":3,"text":"자막"}`, 사진은 `{"image":...,"from":...,"to":...}`.
5. `python tools/shorts_render.py out/<작업>/spec.json out/<작업>/final.mp4`
6. 프레임을 확인하고(예: `ffmpeg -i final.mp4 -vf fps=1/3,tile=5x2 sheet.png`) 결과를 보고한다.

## 4. 반드시 지킬 것
- **사진 저작권:** 블로그·예약 사이트·남의 SNS 사진, 방송 화면 금지. 받은 사진이 그런 것이면 "샘플·업로드 금지" 워터마크를 넣은 시험본만 만든다.
- **AI 장면 표시:** Grok으로 움직인 실제 장소 영상은 업로드 시 "변경되었거나 합성된 콘텐츠" 표시. 건물 모양·간판·가구가 바뀐 클립은 버린다.
- **광고 표시:** 첫 화면 `광고 · 제휴링크 포함`, 설명란 첫 줄 광고 문구. 쿠팡 링크가 있으면 쿠팡 파트너스 고지문.
- **사실:** 확인 안 된 날짜·가격·운영 정보는 쓰지 않는다. "최저가·1위"는 날짜·비교 근거가 있을 때만.
- **비용·게시:** Grok 생성(유료), 결제, 실제 게시는 사용자 확인 후에만.
- **비밀값:** `XAI_API_KEY`, 쿠팡·인포크 키는 환경변수나 `.env`(git 제외)로만. 커밋 금지.

## 5. 개발 규칙
- 테스트: `pip install -r requirements.txt` 후 `pytest`. 네트워크 없이 통과해야 한다 (외부 API는 requests-mock으로).
- 영상 도구를 바꾸면 `tests/test_shorts_render.py`, `tests/test_grok_video.py`를 함께 갱신한다.
- 결과물(mp4, 사진)은 커밋하지 않는다.
