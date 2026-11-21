# Codex에서 청귤트립 쇼츠 만들기 (영상: Grok)

> OpenAI Codex는 저장소 맨 위의 `AGENTS.md`를 자동으로 읽습니다. 그래서 이 저장소를 Codex로 열면 채널 규칙·영상 방법을 따로 설명할 필요가 없습니다.
> 영상은 **xAI Grok Imagine**(사진 → 움직이는 영상)으로 만들고, 자막·광고 표시·엔딩은 저장소의 `tools/shorts_render.py`가 붙입니다.

## 1. 준비 (처음 한 번)
| 할 일 | 방법 |
|---|---|
| Codex에서 이 저장소 열기 | Codex 앱(클라우드)에서 GitHub 저장소 `shinmoney7-cyber/-` 연결, 또는 PC에서 `git clone` 후 그 폴더에서 `codex` 실행 |
| 웹 검색 켜기 | 날짜·가격 조사에 필요. Codex CLI는 `codex --search`, Codex 앱은 환경 설정에서 인터넷 접속 허용 |
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
