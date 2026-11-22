# Codex에서 청귤트립 쇼츠 만들기 (영상: Grok)

> OpenAI Codex는 저장소 맨 위의 `AGENTS.md`를 자동으로 읽습니다. 그래서 이 저장소를 Codex로 열면 채널 규칙·영상 방법을 따로 설명할 필요가 없습니다.
> 영상은 **xAI Grok Imagine**(사진 → 움직이는 영상)으로 만들고, 자막·광고 표시·엔딩은 저장소의 `tools/shorts_render.py`가 붙입니다.

## 0. 원샷 프롬프트: 기획부터 Grok 영상까지 (Codex에 그대로 붙여 넣기)

```
너는 여행 쇼츠 채널 「청귤트립」의 기획자 겸 영상 감독이다. AGENTS.md와
docs/travel-shorts/MASTER_PROMPT_FINAL.md 규칙을 먼저 읽고 그대로 따른다. 답은 한국어.

[입력]
- 오늘 날짜: {2026-11-24}
- 편 번호: {#01}
- 주제: {비움 = 캘린더/수익 점수 1위 자동 선택 | 예: 후쿠오카·유후인 료칸 3박}
- 타깃: {A 5060·가족 / B 커플 / 비움}
- 사진 폴더: {out/2026-11-24_#01/photos/ (01.jpg~08.jpg) / 아직 없음}
- 영상 방식: {전체 Grok / 절약형(훅·대표 2컷만 Grok)}
- 제휴 가입: {쿠팡파트너스만}

[1단계 기획] 웹 검색으로 날짜·가격·장소·가는 법·숙소 3곳·주의사항을 확인하고 항목마다 출처와 확인일을 붙인다.
[충돌]/[오래됨]/[확인 필요] 정보는 자막에 쓰지 않는다. 결과를 out/{날짜}_{번호}/plan.md에 저장:
 - 30초 장면표(9~11장면): # / 시간 / 화면 / 카메라 / 효과 / 자막(12자 이내) / 내레이션(1초 4~5자) / 사진 파일 / Grok 사용 여부
 - 정보 카드 2장("이런 분께 추천" 3줄, "가기 전 꼭 확인" 3줄), 엔딩 "청귤트립 · 정보는 프로필 링크 #번호"
 - 상품 세트 3~5개, 업로드 패키지(제목 5안·설명란·고정댓글·릴스·틱톡·네이버 클립·인포크 카드), 점검표

[1.5단계 사진 자동 준비] 사진 폴더가 비어 있으면:
 - 장면표의 사진 파일마다 검색어(한국어·영어)를 정해 out/{작업}/photo_plan.json 작성
 - python tools/photo_sourcing.py out/{작업}/photo_plan.json out/{작업}/photos
   (한국관광공사 공공누리·Wikimedia CC0/CC BY·Pexels·Pixabay·Unsplash만, credits.txt 자동 생성)
 - 받은 사진을 열어 보고 장면에 안 맞으면 검색어를 바꿔 다시 시도
 - 그래도 없는 장면(특정 호텔 객실·수영장 등)은 웹 검색으로 공식 사진 페이지·연락처를 찾아
   photo_leads.md에 후보 링크와 숙소에 보낼 사진 사용 허락 요청 문구만 정리한다. 이런 사진은 내려받지 않는다
 - credits.txt 내용을 설명란 사진 출처에 넣는다

[2단계 Grok 프롬프트] 사진마다 Grok Imagine 영어 프롬프트를 grok_prompts.md에 표로 쓴다:
 | 사진 | 프롬프트 | 생성 길이(초) | 사용 구간 start/dur |
 형식: "{카메라 1개}. {움직일 것만 1~2개}. {빛·시간대}. Keep the building, room layout, furniture,
 signs and logos exactly as in the photo. No people added, no text, no new objects.
 Realistic travel footage, natural colors, smooth and stable, vertical 9:16."
 - 사진을 직접 열어 보고, 실제로 있는 것(물·김·커튼·나뭇잎·조명·구름)만 움직이게 쓴다
 - 연속 두 장면에 같은 카메라 움직임 금지, 훅은 클로즈업 push-in
 - 마지막 줄에 총 생성량(클립 수 × 초)을 적고 멈춘다 → 내가 "OK"하면 3단계

[3단계 생성] (내 OK 후에만, 유료)
 - 처음 1장은 --dry-run으로 요청 내용을 보여 주고 확인받는다
 - python tools/grok_video.py photos/NN.jpg "<프롬프트>" clips/NN.mp4 --duration 6
 - 각 클립에서 1초 간격 프레임을 뽑아 확인: 건물·간판·가구 변형, 새 사람, 깨진 얼굴이 있으면
   그 클립은 버리고 프롬프트를 더 보수적으로 바꿔 1회만 재생성. 그래도 나쁘면 사진 장면(카메라 효과)으로 대체

[4단계 합치기]
 - spec.json 작성: Grok 클립은 {"video":"clips/NN.mp4","start":..,"dur":..,"text":..},
   대체 장면은 {"image":"photos/NN.jpg","from":..,"to":..}, 카드 2장 + 엔딩,
   badge "광고 · 제휴링크 포함", 길이 합계 − (장면 수−1)×0.3 = 29.5~31초
 - python tools/shorts_render.py out/{작업}/spec.json out/{작업}/final.mp4
 - ffmpeg로 3초 간격 프레임 시트를 만들어 자막 겹침·잘림을 확인하고 고친다

[보고] 최종 파일 경로, 사용한 Grok 생성량, 버린 클립과 이유, 업로드 시 체크할 것
(유료 광고 포함 / 합성 콘텐츠 표시 / 음원 저작권)을 표로 알려 준다.
하지 말 것: 내 OK 전 Grok 생성, 게시, 사진 저작권이 불분명한 사진 사용, 확인 안 된 사실 쓰기.
```

## 1. 준비 (처음 한 번)
| 할 일 | 방법 |
|---|---|
| Codex에서 이 저장소 열기 | Codex 앱(클라우드)에서 GitHub 저장소 `shinmoney7-cyber/-` 연결, 또는 PC에서 `git clone` 후 그 폴더에서 `codex` 실행 |
| 웹 검색 켜기 | 날짜·가격 조사에 필요. Codex CLI는 `codex --search`, Codex 앱은 환경 설정에서 인터넷 접속 허용 |
| 사진 API 키 (무료) | 한국관광공사 TourAPI(data.go.kr) `KTO_API_KEY`, Pexels `PEXELS_API_KEY`, Pixabay `PIXABAY_API_KEY`, Unsplash `UNSPLASH_ACCESS_KEY` — 하나만 있어도 동작, Wikimedia는 키 불필요 |
| Grok API 키 | xAI 콘솔(console.x.ai)에서 발급 → Codex 환경변수(비밀값)에 `XAI_API_KEY`로 저장. 채팅에 붙여 넣지 말 것 |
| 인터넷 허용 주소 (클라우드) | `api.x.ai`와 Grok이 돌려주는 영상 다운로드 주소, 검색에 쓰는 사이트들 |
| 패키지 | `pip install -r requirements.txt` (ffmpeg 필요) |

> **API 없이 쓰는 방법:** grok.com이나 X 앱의 Grok Imagine에 사진을 올리고 4번 프롬프트를 붙여 넣어 영상을 받습니다. 받은 mp4를 `out/<작업>/clips/`에 넣고 Codex에 "이 클립으로 영상 합쳐줘"라고 하면 됩니다.

## 2. Codex에 이렇게 말하세요 (복사용)

### ① 오늘 기획 만들기
```
AGENTS.md와 docs/travel-shorts/MASTER_PROMPT_FINAL.md 규칙대로 오늘 청귤트립 쇼츠 1편을 기획해줘.
- 오늘 날짜: 2026-11-24
- 편 번호: #01
- 제휴 가입: 쿠팡파트너스만
- 최근 기록: 없음
웹 검색으로 날짜·가격·장소를 확인하고 출처와 확인일을 붙여.
결과는 out/2026-11-24_#01/plan.md에 저장하고, 장면마다 Grok Imagine 영어 프롬프트도 넣어줘.
```

### ② 사진으로 영상 만들기
```
out/2026-11-24_#01/photos/ 에 사진 8장을 넣었어.
plan.md 장면표대로 각 사진의 Grok 프롬프트를 확정하고, 생성 비용(초 × 클립 수)을 먼저 알려줘.
내가 OK하면 tools/grok_video.py로 클립을 만들고, spec.json을 만들어서 tools/shorts_render.py로 30초 최종본을 만들어줘.
```

### ③ 고치기
```
3번 장면 자막을 "하늘과 이어진 수영장"으로 바꾸고, 5번 클립은 1초부터 써줘. 다시 렌더링해줘.
```

## 3. 비용 아끼는 법
| 방식 | Grok 클립 | 언제 |
|---|---|---|
| **전체 Grok** | 사진 7~8장 모두 6초 클립 → 앞뒤 잘라 2~3.5초씩 사용 | 대표 영상, 숙소 홍보 |
| **절약형** | 훅·대표 장면 2컷만 Grok, 나머지는 사진 카메라 효과(무료) | 매일 올리는 일반 편 |

Grok 요금은 생성한 초 단위로 매겨집니다. 생성 전 Codex가 "클립 N개 × 6초"를 알려 주면 xAI 콘솔의 현재 단가로 확인하세요.

## 4. Grok Imagine 프롬프트 형식 (사진 → 영상)
사진이 첫 장면이 되고, 프롬프트는 **무엇이 어떻게 움직이는지**만 영어로 짧게 씁니다.

```
{카메라 움직임}. {움직일 것만 1~2개}. {빛·시간대}. Keep the building, room layout, furniture, signs and logos exactly as in the photo. No people added, no text, no new objects. Realistic travel footage, natural colors, smooth and stable, vertical 9:16.
```

| 장면 | 프롬프트 |
|---|---|
| 수영장 (낮) | `Slow dolly-in at water level. Only the pool water gently ripples, sunlight caustics shimmer on the pool floor. Bright clear morning. Keep the building, skyline and pool shape exactly as in the photo. No people added, no text. Realistic travel footage, vertical 9:16.` |
| 온수풀 (겨울) | `Very slow push-in. Soft steam rises from the warm water, light ripples on the surface. Cold blue dusk with warm pool lights. Keep everything else unchanged. No people.` |
| 수영장 (야경) | `Slow lateral slide from left to right. Water ripples reflect the city lights, underwater lights sparkle. Night. Keep the layout unchanged. No people.` |
| 오션뷰 객실 | `Slow dolly-in toward the window. Sheer curtains sway gently, waves move slowly outside. Soft morning light. Keep the room and furniture exactly as in the photo.` |
| 라운지 | `Slow push-in toward the plant. Sunlight and leaf shadows drift slowly across the floor and sofa. Warm afternoon light. Keep furniture unchanged. No people.` |
| 침실 | `Slow pull-back revealing the whole room. Bedside lamp glows warmly. Evening mood. Keep the room exactly as in the photo.` |
| 단풍길 | `Slow forward dolly along the path. Red and yellow leaves fall slowly, branches sway in a light breeze. Golden hour.` |
| 바다·해변 | `Slow rise and tilt down like a drone. Waves roll gently onto the shore, clouds drift slowly. Clear blue day.` |
| 기차 창밖 | `Static camera inside the train. Autumn mountains pass from right to left, faint window reflection.` |
| 온천·료칸 | `Slow push-in. Steam rises softly from the open-air bath, light snow falls. Quiet winter evening.` |
| 음식 | `Slow orbit around the bowl. Steam rises, the broth surface glistens. Warm restaurant light.` |
| 야경 도시 | `Slow push-in. City lights twinkle, light trails of cars move on the road. Blue hour.` |

**Grok 클립 고르는 기준**
- 건물 모양, 간판 글자, 가구 배치가 바뀌었으면 버리고 다시 생성 (실제와 다르면 허위 광고)
- 사람이 새로 생겼거나 얼굴이 이상하면 버림
- 6초 중 가장 안정적인 2~3.5초만 `start`/`dur`로 잘라 씀

## 5. spec.json 예시 (Grok 클립 + 사진 섞기)
```json
{
  "size": [720, 1280], "fps": 30, "transition": 0.3,
  "badge": "광고 · 제휴링크 포함",
  "scenes": [
    {"video": "clips/01.mp4", "start": 0.5, "dur": 2.2, "text": "속초에 이런 수영장이?", "text_pos": "top"},
    {"video": "clips/02.mp4", "start": 1.0, "dur": 3.0, "text": "하늘과 이어진 인피니티풀", "text_pos": "top"},
    {"image": "photos/03.jpg", "dur": 3.0, "from": {"z": 1.0}, "to": {"z": 1.3, "cy": 0.4}, "text": "햇살 가득한 라운지"},
    {"video": "clips/04.mp4", "start": 0.5, "dur": 3.2, "text": "빔프로젝터로 영화 한 편"},
    {"card": true, "bg": "photos/01.jpg", "dur": 3.2, "title": "이런 분께 추천", "lines": ["부모님 모시고 호캉스", "아이와 물놀이", "커플 기념일 여행"]},
    {"card": true, "bg": "photos/05.jpg", "dur": 3.0, "title": "가기 전 꼭 확인", "lines": ["수영장 운영 기간·시간", "온수 여부", "투숙객 전용 여부"]},
    {"end": true, "dur": 2.4, "title": "청귤트립", "lines": ["정보는 프로필 링크 #P5", "구독하고 다음 여행도 같이 가요"]}
  ]
}
```
장면 길이 합계 − (장면 수 − 1) × 0.3 = 29.5~31초가 되게 맞춥니다.

## 6. 짝수일 자동 실행과의 관계
- 짝수일 08:40 자동 실행(Claude 예약 작업)은 **기획 메일**까지 만듭니다.
- 승인 후 영상 제작은 Codex에서 ②번 지시문으로 하면 됩니다. 기획 메일의 장면표와 Grok 프롬프트를 `out/<날짜>_#번호/plan.md`에 붙여 넣고 시작하세요.
