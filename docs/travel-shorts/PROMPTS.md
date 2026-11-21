# 청귤트립 여행쇼츠 프롬프트 모음

> 용도별로 복사해서 Claude(또는 다른 AI)에 붙여 넣고 `{ }` 부분만 채우세요.
> 1번이 기본입니다. 사진이 있으면 2번, AI 영상 장면이 필요하면 3번을 이어서 씁니다.

| # | 프롬프트 | 언제 |
|---|---|---|
| 1 | 마스터 기획 (대본·장면·카메라·자막·설명란 한 번에) | 새 영상 기획할 때 항상 |
| 2 | 사진 → 장면 구성 (렌더 도구용 JSON까지) | 사진 7~8장을 받았을 때 |
| 3 | AI 영상 장면 (사진 → 움직이는 영상) | 수영장 물결, 드론 느낌 등 특정 컷만 |
| 4 | 제목·썸네일·해시태그 10안 | 업로드 직전 |
| 5 | 성과 분석 → 다음 영상 | 매주 월요일 |

---

## 1. 마스터 기획 프롬프트

```
너는 유튜브 쇼츠·인스타 릴스·틱톡용 여행 쇼츠 전문 기획자이자 영상 감독이다.
채널 「청귤트립」의 30초 세로 영상(9:16) 한 편을 아래 조건으로 완성해라.

[채널 정보]
- 채널: 청귤트립 (상큼하게 떠나고, 알뜰하게 돌아오는 여행)
- 주 시청자: 50~60대 부부, 부모님 모시고 여행 가는 30~40대 자녀
- 말투: 친근한 존댓말("~해요", "~하세요"). 반말·유행어·과장 금지
- 색: 청귤 초록 #7CB342, 귤 주황 #FFA726(가격·숫자 강조), 글자 진회색 #263238
- 재생목록: 레몬레일(기차) / 청귤드라이브(자동차·펜션·호텔) / 햇살티켓(입장권·할인) / 여행비타민(꿀팁·준비물) / 청귤비행(해외·비행기)

[이번 영상]
- 주제: {예: 속초 홈마리나 호텔 1박 후기}
- 재생목록: {청귤드라이브}
- 영상 번호: {#P5}
- 핵심 메시지 한 줄: {예: 한겨울에도 수영되는 오션뷰 호텔}
- 확인된 사실만: {가격, 위치, 운영 시간, 교통 등. 확인 날짜 포함. 없으면 "없음"}
- 사용할 사진/영상: {장면별 사진 설명 7~8개. 없으면 "없음 - 촬영 목록도 만들어줘"}
- 연결할 링크: {숙소 아고다 / 쿠팡 방수팩 등}

[반드시 지킬 규칙]
1. 길이 28~32초. 장면 9~11개, 장면당 2~3.5초.
2. 0~2초 훅: 질문형 또는 숫자·손해형. 첫 화면만 봐도 무슨 영상인지 알게.
3. 장면 하나에 정보 하나. 자막은 12자 이내, 화면에 2줄 넘지 않게.
4. 내 [확인된 사실]에 없는 가격·시간·층수·수온·운영 기간을 지어내지 마라.
   필요하면 "[확인 필요: 무엇]"이라고 표시해라.
5. "최저가", "무조건", "역대급" 같은 근거 없는 최상급 표현 금지.
6. 0~2초 화면 왼쪽 위에 작은 글씨 "광고 · 제휴링크 포함" 표시.
7. 마지막 장면: "청귤트립" 로고 + "정보는 프로필 링크 {영상번호}".
8. 실제 장소를 AI로 만든 장면은 "[AI]"로 표시하고 분위기 컷에만 써라.

[출력 형식 - 이 순서 그대로]

A. 한 줄 콘셉트와 타깃 (2줄)

B. 장면표 (표)
| # | 시간 | 화면(무엇을 보여주나) | 카메라 움직임 | 효과 | 큰 자막 | 내레이션 |
- 카메라 움직임은 다음 중에서 고르고 장면마다 바꿔라:
  빠른 줌인 / 천천히 줌인 / 천천히 줌아웃 / 좌→우 패닝 / 우→좌 패닝 / 아래→위 틸트 / 위→아래 틸트 / 고정
- 효과 예: 수면 물결, 김 피어오름, 빛 반짝임, 글자 하나씩 등장, 없음
- 연속된 두 장면에 같은 카메라 움직임을 쓰지 마라.
- 내레이션은 장면 길이 안에 읽을 수 있게(1초에 4~5글자).

C. 정보 카드 2장 (장면표 안에 포함)
- "이런 분께 추천" 3줄
- "가기 전 꼭 확인" 3줄 (운영 시간·요금·예약 조건처럼 바뀌기 쉬운 것)

D. 플랫폼별 버전
- 유튜브 쇼츠: 제목(40자 이내, 키워드 앞쪽) / 설명란 / 고정댓글
- 인스타 릴스: 15초 축약 장면 순서 / 캡션 / 해시태그 5개
- 틱톡: 첫 자막을 질문형으로 바꾼 버전
- 네이버 클립: 검색형 제목

E. 설명란 (아래 틀 그대로, 광고 문구가 첫 줄)
광고 | 이 영상의 링크로 예약·구매하면 제휴 수수료를 받을 수 있습니다.
{요약 한 줄}
{장소·상품 ①②③}
※ {날짜} 기준 정보입니다. 방문 전 공식 안내를 확인하세요.
📌 숙소·투어·준비물 → 프로필 링크 ({영상번호})
{쿠팡 링크가 있을 때만} 이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.
{사진 출처}
#청귤트립 {해시태그 5~7개}

F. 인포크 링크 카드 (카드 제목 / 연결 업체 / 영상번호)

G. 촬영 목록 (사진이 부족할 때): 찍을 장면 8개, 각 장면의 구도와 시간대

H. 확인 필요 목록: 업로드 전에 내가 직접 확인해야 할 사실
```

---

## 2. 사진 → 장면 구성 프롬프트 (렌더 도구용)

사진 7~8장을 첨부하고 사용합니다. 결과 JSON을 `tools/shorts_render.py`에 그대로 넣으면 영상이 나옵니다.

```
첨부한 사진 {8}장으로 「청귤트립」 30초 세로 쇼츠를 구성해라.
주제: {속초 홈마리나 호텔}, 영상 번호: {#P5}

1단계 - 사진 분석 (표)
| 파일명 | 무엇이 찍혔나 | 가장 강한 부분(피사체 위치 x,y 0~1) | 화질 문제 | 추천 역할(훅/본문/카드배경/엔딩) |

2단계 - 순서 정하기
- 가장 눈길을 끄는 사진을 1번(훅)으로. 같은 사진을 2번에서 넓게 한 번 더 써도 된다.
- 흐름: 훅 → 대표 시설 → 공간 → 객실 → 디테일 → 추천 카드 → 확인 카드 → 엔딩
- 비슷한 사진이 연속되지 않게.

3단계 - 카메라 설계
- 각 장면의 시작/끝 프레이밍을 z(1.0=사진 전체에서 세로로 자른 최대 범위, 클수록 확대),
  cx, cy(화면 중심, 0~1)로 정해라.
- 줌인: z 1.0→1.3 / 줌아웃: 1.45→1.0 / 패닝: cx 0.2→0.8 / 틸트: cy 0.7→0.3
- 훅 장면은 z 1.6 이상 클로즈업에서 시작.
- 수영장·바다·호수처럼 물이 있는 사진은 "ripple": {"y0": 수면이 시작되는 세로 위치 0~1, "amp": 5}
- 장면 길이 합계 - (장면 수-1)×0.3 = 29.5~31초가 되게.

4단계 - 아래 JSON 형식으로만 출력 (설명 없이)
{
  "size": [720, 1280], "fps": 30, "transition": 0.3,
  "badge": "광고 · 제휴링크 포함",
  "scenes": [
    {"image": "파일명", "dur": 2.2, "from": {"z": 1.7, "cx": 0.3, "cy": 0.7}, "to": {"z": 1.35, "cx": 0.35, "cy": 0.65},
     "ripple": {"y0": 0.66, "amp": 5}, "text": "12자 이내 자막", "text_pos": "top|middle|bottom"},
    {"card": true, "bg": "파일명", "dur": 3.2, "title": "이런 분께 추천", "lines": ["...", "...", "..."]},
    {"card": true, "bg": "파일명", "dur": 3.0, "title": "가기 전 꼭 확인", "lines": ["...", "...", "..."]},
    {"end": true, "dur": 2.4, "title": "청귤트립", "lines": ["정보는 프로필 링크 #P5", "구독하고 다음 여행도 같이 가요"]}
  ]
}

규칙
- 자막은 피사체를 가리지 않는 위치(text_pos)를 골라라.
- 사진에 없는 사실(가격, 수온, 층수 등)은 자막에 쓰지 마라.
- 다른 사람의 워터마크·글씨가 있는 사진은 "사용 불가"로 표시하고 빼라.
```

---

## 3. AI 영상 장면 프롬프트 (사진 → 움직이는 영상)

이미지→영상 AI 도구(Higgsfield, Kling 등)에 사진과 함께 넣습니다. **영어가 더 정확하게 먹힙니다.** 장면 하나(5초 안팎)씩 만듭니다.

### 기본 틀
```
[SUBJECT] {what is in the photo, one line}
[MOTION] {only what should move}
[CAMERA] {one camera move}
[LIGHT] {time of day / mood}
[KEEP] keep the building, room layout, furniture and logos exactly as in the photo; no new objects, no people added, no text
[STYLE] realistic travel footage, smartphone 4K, natural colors, vertical 9:16
```
네거티브(지원되는 도구만): `warped buildings, melting furniture, extra people, distorted text, flicker, cartoon, oversaturated`

### 장면별 완성 예시

| 장면 | 프롬프트 |
|---|---|
| 수영장 (낮) | `Rooftop infinity pool overlooking the city. Only the water gently ripples, sunlight caustics shimmer on the pool floor, the pool edge water spills softly. Slow dolly-in at water level. Bright clear morning. Keep the building, skyline and pool shape exactly as in the photo; no people added, no text. Realistic travel footage, vertical 9:16.` |
| 수영장 (온수·겨울) | `Heated outdoor pool in winter. Soft steam rises from the warm water, light ripples on the surface. Static camera with very slow push-in. Cold blue dusk, warm pool lights. Keep everything else unchanged; no people.` |
| 수영장 (야경) | `Infinity pool at night. Water ripples reflect the city lights, underwater lights glow and sparkle. Slow lateral slide from left to right. Keep the layout unchanged; no people.` |
| 오션뷰 객실 | `Hotel room with a large window facing the sea. Sheer curtains sway gently in the breeze, waves move slowly outside. Slow dolly-in toward the window. Soft morning light. Keep the room and furniture exactly as in the photo.` |
| 라운지·카페 | `Sunlit hotel lounge. Sunlight and leaf shadows drift slowly across the floor and sofa, plant leaves move slightly. Slow push-in toward the plant. Warm afternoon light. Keep furniture unchanged; no people.` |
| 침실 | `Cozy hotel twin room. Bedside lamp light flickers warmly, very subtle. Slow pull-back revealing the whole room. Evening mood. Keep the room exactly as in the photo.` |
| 단풍길·숲 | `Autumn forest path with red and yellow maple trees. Leaves fall slowly and branches sway in a light breeze. Slow forward dolly along the path. Golden hour.` |
| 바다·해변 | `Seaside view. Waves roll gently onto the shore, clouds drift slowly. Slow aerial drone-like rise and tilt down. Clear blue day.` |
| 기차 창밖 | `View from a train window passing autumn mountains. Scenery moves from right to left, slight window reflection. Static camera inside the train.` |
| 온천·료칸 | `Open-air hot spring at a Japanese ryokan. Steam rises softly from the water, light snow falls. Slow push-in. Quiet winter evening.` |
| 음식 | `Hot ramen bowl on a table. Steam rises, broth surface glistens. Slow orbit around the bowl. Warm restaurant light.` |

### AI 장면 규칙
- 영상 한 편에 AI 장면은 **1~2컷**만 (훅, 대표 컷).
- 실제 장소를 AI로 움직였으면 업로드 시 **"변경되었거나 합성된 콘텐츠" 표시**.
- 결과에서 건물 모양·간판·가구가 바뀌었으면 버리고 다시 만들 것 (실제와 다르면 허위 광고가 됨).
- 크레딧이 들기 때문에 제작 전 예상 비용을 확인할 것.

---

## 4. 제목·썸네일·해시태그 프롬프트

```
「청귤트립」 여행 쇼츠 업로드용 문구를 만들어라.
영상 내용: {장면표 또는 한 줄 요약}
타깃: 50~60대, 부모님과 여행하는 30~40대

1. 제목 10안 (40자 이내)
   - 유형별: 질문형 3 / 숫자형 3 / 손해·절약형 2 / 감성형 2
   - 검색 키워드(지역+숙소유형/여행지+꿀팁)를 앞쪽 15자 안에
2. 첫 화면(썸네일) 문구 5안: 8자 이내, 숫자나 질문 포함
3. 해시태그: 큰 태그 3(#국내여행 등) + 중간 3(#속초여행 등) + 작은 3(#속초호캉스 등) + #청귤트립
4. 각 안 옆에 어떤 시청자를 노린 건지 한 줄
금지: "최저가", "무조건", "역대급", 확인 안 된 숫자
```

---

## 5. 주간 성과 분석 프롬프트

```
지난주 「청귤트립」 영상 성과다. 표: {영상번호 / 제목 / 조회수 / 평균 시청률 / 링크 클릭 / 구매·예약 / 수익}

1. 클릭률(클릭÷조회수) 계산, 0.3% 이상 / 0.1~0.3% / 0.1% 미만으로 나눠라.
2. 조회수는 높은데 클릭이 낮은 영상 → CTA·링크 문제. 조회수가 낮은 영상 → 첫 2초 문제. 각각 원인과 고칠 점.
3. 잘 된 영상의 공통점 (재생목록, 훅 유형, 길이, 지역, 숙소 유형)
4. 다음 주 5편 추천: 제목 / 재생목록 / 왜 / 연결 링크
5. 그만둘 소재
```
