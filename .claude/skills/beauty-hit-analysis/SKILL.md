---
name: beauty-hit-analysis
description: 다른 제작자의 잘 나가는(매출·수익 상위) 뷰티 쇼츠를 실제 데이터로 분석해서, 제품 유형마다 후킹·길이·구성·표정·SEO 패턴을 뽑고 뷰티쇼츠 대본 스튜디오(docs/beauty-shorts/studio.html)와 납품 대본에 반영한다. "잘 나가는 영상 분석", "벤치마크", "수익 높은 영상 따라", "히트 영상 반영" 요청에 사용.
---

# 뷰티 히트 영상 분석 → 제품별 반영

모든 설명·결과는 한국어로 쓴다.

## 1. 데이터 모으기 (실제 수치만)

- **TikTok Shop 데이터 도구**(Topview `use_tiktok_data` → `call_tool`)를 쓴다. 현재 지원 지역은 미국(US)·일본(JP)뿐이다. 한국 쇼츠 수익 데이터는 이 도구로 볼 수 없다.
  - `td_hashtag_v2_search` — 키워드로 해시태그를 찾고 기간 매출(GMV)로 정렬. `{"req":{"keyword":"serum","region":"US","period":"90d","sortField":"localGmvPeriod"}}`
  - `td_hashtag_v2_video_list` — 해시태그 안의 영상을 매출순으로. `sortField`: `localGmv`(매출) · `videoRevenuePerThousandPlays`(조회 1천 회당 매출) · `videoConversionRate`(구매 전환율)
  - 받는 값: 설명글(`videoDesc`), 길이, 조회·좋아요·공유·댓글, 매출(USD), 판매 수, 평균가, 전환율, 조회 1천 회당 매출
- 제품 유형별 해시태그 예: 기초(faceserum·moisturizer) · 기능성(retinol·darkspot·niacinamide) · 선케어(sunscreen) · 베이스(foundation·cushion) · 립(liptint·lipstick) · 아이(eyeshadow·mascara) · 치크(blush·highlighter) · 클렌징(cleansingbalm·cleansingoil)
- 유튜브 채널 정보가 필요하면 `use_youtube_kol`(채널·최근 영상), 국내 사례는 웹 검색으로 보완하고 출처를 남긴다.
- 영상 파일(cdn.tabcut.com)은 이 환경에서 막혀 있어 화면은 못 본다. 설명글·수치로만 분석하고 그 한계를 결과에 적는다.
- 수치는 지어내지 않는다. 매출은 TikTok Shop 판매액이지 제작자 수수료가 아니다.

## 2. 분석 항목 (제품 유형마다)

1. **길이**: 매출 상위 10개 영상의 길이 중앙값, 30초 미만·30~60초·60초 이상 비율
2. **수익 효율**: 조회 1천 회당 매출, 전환율 — 조회수보다 이 값이 높은 영상의 공통점을 본다
3. **후킹 문구**: 설명글·첫 문장에서 반복되는 표현을 원문 그대로 인용하고 한국어로 바꾼다 (예: "genuinely putting you guys on…" → "이건 진짜 알려드려야 해서")
4. **구성**: 문제 제기 → 시연 → 결과 → 링크 순서인지, 가격·구성 강조인지, 같은 제작자가 여러 편을 올렸는지
5. **반응**: 댓글이 많은 영상(질문 → 구매 문의)과 공유가 많은 영상의 차이
6. **가격대**: 평균가와 매출의 관계

## 3. 저장 형식

`docs/beauty-shorts/benchmark/<유형>.json` (유형 키: skin · functional · sun · base · lip · eye · cheek · cleansing)

```json
{ "key": "skin", "hashtags": ["faceserum"], "period": "2026-07~2026-10, 미국 TikTok Shop",
  "videos": [{ "desc": "...", "sec": 34.7, "plays": 147107, "gmv": 5431.6, "sold": 367, "rpm": 36.9, "cvr": 0.25, "eng": 0.49, "url": "https://www.tiktok.com/..." }],
  "stats": { "medianSec": 35, "avgRpm": 28.1, "share_under30s": 30, "share_30to60s": 50, "share_over60s": 20 },
  "patterns": ["한국어 인사이트 ..."],
  "hooks_ko": ["0~2초 한국어 후킹 ..."] }
```

## 4. 스튜디오·대본에 반영

1. `python docs/beauty-shorts/build_benchmark.py` — `benchmark/*.json`을 `studio.html`의 `BENCH` 데이터로 넣는다.
2. 스튜디오 "잘 나가는 영상 분석" 칸에 유형별 수치·패턴·상위 영상 링크가 보이고, 대본 5종(G1~G5)을 만들 때:
   - 후킹 문구 10개에 `hooks_ko`가 먼저 들어간다
   - 기획안에 "히트 영상 기준 권장 길이·수익 효율" 줄이 붙는다
3. 납품 대본(`shinjh-serum-01_납품대본.md`)에 해당 유형 분석 요약을 추가하고 Word·PDF를 다시 만든다 (`build_print.py`).

## 5. 지켜야 할 것

- 남의 영상 문장·화면을 그대로 베끼지 않는다. 패턴(구조·길이·후킹 방식)만 가져와 우리 제품·우리 말투로 바꾼다.
- 해외 영상의 효능 표현(예: 여드름·곰팡이·탈모 개선)은 한국 화장품법상 쓸 수 없는 경우가 많다. 한국어로 바꿀 때 스튜디오의 주의 표현 기준으로 걸러낸다.
- AI 모델로 만들 때는 "써봤어요" 같은 사용 경험 표현을 빼고 시연형으로 바꾼다.
