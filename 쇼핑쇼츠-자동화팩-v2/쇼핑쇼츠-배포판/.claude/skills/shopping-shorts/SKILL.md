---
name: shopping-shorts
description: 쿠팡 파트너스용 쇼핑 쇼츠(세로 9:16 리뷰형 숏폼)를 처음부터 끝까지 제작한다. 소스 영상 다운로드 → 대본 → AI 나레이션 → 컷편집 → Remotion 렌더 → 검수. "쇼츠 만들어줘", "쇼핑쇼츠", "이 상품으로 영상 만들어줘", "틱톡 링크로 쇼츠", "숏폼 만들어줘" 같은 요청에 사용한다.
---

# 쇼핑쇼츠 제작

실물 영상 컷편집 + AI 음성 나레이션 형태의 세로 쇼츠를 만든다.
결과물: `remotion-project/out/shorts.mp4` (1080×1920 · 30fps · 15~25초).

**이 팩은 Node만 쓴다. Python은 필요 없다.** 도구는 전부 `tools/*.js`이고
`node tools/파일.js` 로 실행한다. 사용자가 파이썬 얘기를 꺼내면 필요 없다고 알려준다.

## 시작 전 반드시 확인

작업을 시작하기 전에 `node tools/check.js`를 실행해 환경을 점검한다.
빠진 도구가 있으면 **먼저 설치를 안내하고 사용자 허락을 받은 뒤** 진행한다.
없는 상태로 진행하면 3단계 이후에서 반드시 실패한다.

필요한 것: Node.js LTS · `ffmpeg` · `ffprobe` · `yt-dlp` · `tools/node_modules`

**설치 여부를 `where` 로 판단하지 말 것.** 윈도우는 실행되지 않는 껍데기를 PATH에
심어두는 경우가 있어서, 있는데 안 되는 상태를 못 걸러낸다. 반드시 한 번 실행해 본다
(`node -v`, `ffmpeg -version`). `check.js`가 이미 그렇게 하고 있다.

빠진 게 있으면 winget으로 깐다. 깔고 나면 **새 터미널에서만 인식**된다.

```
winget install -e --id OpenJS.NodeJS.LTS
winget install -e --id Gyan.FFmpeg
winget install -e --id yt-dlp.yt-dlp
```

`tools/node_modules`가 없으면 `cd tools && npm install`.
(`tools/.npmrc`에 `ignore-scripts=true`가 있어야 한다. msedge-tts의 preinstall이
npm 설치를 거부하기 때문이다. 이 파일을 지우지 말 것.)

## 사용자에게 먼저 물어볼 것

1. **상품명**
2. **소스 영상** — 틱톡/더우인 링크들, 또는 이미 가지고 있는 영상 파일
3. **쿠팡 파트너스 링크** (없으면 나중에 넣으라고 안내하고 진행)

소스 링크가 없다면: 틱톡에서 상품 키워드로 검색하되, **중국어 키워드로 재검색**하면
소재 품질이 훨씬 좋다고 안내한다 (예: 무타공 전동 커튼 → `免打孔电动窗帘`).

---

## 1단계 — 소스 수집

```
yt-dlp -P tools/src -o "%(id)s.%(ext)s" -f "b[vcodec!=none]/bv*+ba/bv*" --no-simulate <링크들>
```

**`--print` 를 쓸 거면 반드시 `--no-simulate` 를 같이 넘긴다.**
`--print` 는 simulate 를 켜기 때문에, 빼먹으면 메타데이터만 찍히고 **파일은 하나도 안 받아진다.**
(로그는 성공한 것처럼 보이는데 `tools/src` 가 비어 있으면 이걸 의심한다.)

**실패할 때 — 순서대로 시도한다:**

1. `Unexpected response from webpage request` → yt-dlp 가 낡았다.
   `winget upgrade -e --id yt-dlp.yt-dlp` (또는 `yt-dlp -U`)
2. 틱톡 챌린지는 **재시도하면 대부분 뚫린다.** 링크마다 5~8회, 5초 간격이 정상이다.

   ```powershell
   foreach ($u in $urls) {
     for ($i=1; $i -le 8; $i++) {
       yt-dlp -P tools/src -o "%(id)s.%(ext)s" -f "b[vcodec!=none]/bv*+ba/bv*" --no-simulate --quiet $u 2>$null
       if ($?) { break }
       Start-Sleep -Seconds 5
     }
   }
   ```

3. 그래도 전부 실패하면 **tikwm 공개 API**로 받는다. 틱톡 추출기가 깨진 시기에도 이건 되는 때가 많다.
   (막혔다 뚫렸다를 반복하므로, 안 된다고 단정하지 말고 매번 한 번은 찔러본다.)

   ```
   curl "https://www.tikwm.com/api/?url=<틱톡URL>&hd=1"
   ```

   JSON의 `data.hdplay`(없으면 `data.play`)가 워터마크 없는 mp4 직링크다.
   내려받을 때만 `-A "Mozilla/5.0"` 을 붙인다. 2~3초 간격으로 던진다.
   응답에 `data.images` 배열이 있으면 **포토 슬라이드쇼**라 영상 트랙이 없다. 걸러낸다.
   `Just a moment...` HTML이 오면 클라우드플레어에 막힌 것이니 이 경로는 포기한다.

4. `--cookies-from-browser chrome` 은 크롬이 켜져 있으면 실패한다. 쓰지 않는다.
5. 포토 슬라이드쇼는 쓸 수 없다.
   `-f "b[vcodec!=none]/bv*+ba/bv*"` 로 받아서 `Requested format is not available` 이 뜨면 걸러낸다.

받은 영상마다 `ffprobe`로 해상도·길이를 확인하고, 상품이 다른 영상은 버린다.
링크 10개를 주면 실제로 쓸 만한 건 2~3편인 게 정상이다. 사용자에게 선별 결과를 표로 보고한다.

## 2단계 — 워터마크 실측 (건너뛰지 말 것)

틱톡/더우인 소재는 **상하단에 원작자 워터마크나 영문 고지문이 박혀 있는 경우가 대부분이다.**
추측하지 말고 실측한다.

```
ffmpeg -ss <시각> -i <소스> -frames:v 1 -vf "crop=iw:300:0:0" top.png
ffmpeg -ss <시각> -i <소스> -frames:v 1 -vf "crop=iw:300:0:ih-300" bottom.png
```

위/아래 300px만 잘라낸 프레임을 **직접 눈으로 확인**하고, 가려야 할 픽셀 높이를 정한다.
그만큼 잘라낸 뒤 9:16 비율을 다시 맞춘다.

```
crop=<너비>:<높이>:<x>:<y>
```

예: 1080×1920 소스에서 위 40px, 아래 180px를 버리는 경우 → `crop=956:1700:62:40`
(높이 1700에 맞는 9:16 너비는 956, 가운데 정렬이므로 x=62)

화면 **중앙**에 자막이 박혀 있는 구간은 잘라낼 수 없다. 그 구간은 아예 쓰지 않는다.

## 3단계 — 대본

`대본.txt`에 **자막 한 줄당 한 행**으로 쓴다. 빈 줄과 `#`으로 시작하는 줄은 무시된다.

구조: **훅 → 강점 3 → CTA**, 자막 10줄 내외, 전체 15~25초.

- 1행은 훅. 문제 상황을 질문으로 던진다. ("주방 기름때, 수세미로 문질러도 안 지워지죠?")
- 중간은 강점. 예능식으로 짧게. ("누워서 말만 하면 열림")
- 마지막은 CTA. ("지금 프로필 링크에서 확인하세요")

한 행이 너무 길면 화면에서 두 줄로 넘어간다. **한 행 20자 이내**를 지킨다.

## 4단계 — 나레이션

```
node tools/tts.js
node tools/tighten.js
```

- `tts.js` — `대본.txt`를 읽어 `work/vo_raw.mp3` + `work/timings.json` 생성.
  마이크로소프트 Edge 신경망 음성(`msedge-tts`)을 쓴다. 무료·가입 불필요.
- `tighten.js` — 문장 사이 긴 공백을 0.16초로 줄이고, 줄어든 만큼 자막 start를 당긴다.
  결과를 **자동으로** `remotion-project/public/audio/vo.mp3` 와 `product.json`에 반영한다.

목소리를 바꾸려면: `node tools/tts.js --voice ko-KR-InJoonNeural --rate +5%`
기본값은 `ko-KR-SunHiNeural`(여), `+8%`. 남자는 `ko-KR-InJoonNeural`.

**주의 — 이 두 가지는 반드시 지킨다:**
- 대본 전체를 **한 번에** 합성한다. 줄마다 따로 부르면 문장 흐름이 끊겨 어색해진다.
  (`tts.js`에 이미 반영됨)
- 나레이션 길이는 **반드시 `ffprobe`로 실측**한다. 플레이어 표시 길이는 틀릴 때가 있다.

자막 시작 시각은 Edge 음성의 단어 타임스탬프에서 뽑는다. 어절 분절이 자막 분절과
다를 수 있어서, 문장부호·공백을 지운 **글자 수 누적**으로 경계를 찾는다. 이러면
음성이 어떻게 쪼개든 어긋나지 않는다. (`tts.js`에 이미 반영됨)

일레븐랩스를 쓰고 싶다는 요청이 있으면: 사이트에서 생성한 mp3를
`remotion-project/public/audio/vo.mp3`로 저장하고, 자막 start는 수동으로 실측해
`product.json`에 넣어야 한다고 안내한다. (무료 월 1만자 · 보이스 `Jeong-Ah` 검증됨)

## 5단계 — 컷편집

`tools/cuts.json`을 작성한 뒤:

```
node tools/cut.js
```

`cuts.json` 형식:

```json
{
  "sources": {
    "A": { "file": "src/7607399180432182551.mp4", "crop": "crop=956:1700:62:40" },
    "B": { "file": "src/7625540762968608013.mp4", "crop": "crop=956:1700:62:40" }
  },
  "scenes": {
    "01": [ { "src": "A", "ss": 0.00, "t": 4.00 } ],
    "03": [ { "src": "B", "ss": 4.15, "t": 2.20 }, { "src": "B", "ss": 2.30, "t": 1.80 } ]
  }
}
```

- 한 씬에 여러 구간을 넣으면 순서대로 이어붙인다.
- `crop`은 생략 가능(원본이 이미 깨끗한 9:16이면). 생략하면 스케일만 적용된다.
- `file` 경로는 `tools/` 기준 상대경로다.
- 결과는 `remotion-project/public/clips/01.mp4` … 로 저장된다.

**구간 고르는 법:** 각 소스에서 프레임을 뽑아 내용을 직접 확인한 뒤 고른다.
씬 길이는 `나레이션초 ÷ 씬수`에 맞춘다(5씬 17.2초면 씬당 약 3.4초).

검증된 컷 순서: **문제 상황 훅 → 사용/설치 클로즈업 → 효과가 드러나는 순간 → 결과 → 제품샷 CTA**

## 6단계 — 씬 데이터

`remotion-project/src/data/product.json`을 채운다.
`captions`와 `narrationDuration`은 4단계에서 이미 자동으로 들어가 있다. 나머지만 채운다.

```json
{
  "brand": "브랜드명",
  "productName": "상품명",
  "coupangUrl": "https://link.coupang.com/...",
  "accent": "#2ECC71",
  "bgm": "",
  "scenes": [
    { "type": "hook",    "clip": "clips/01.mp4" },
    { "type": "feature", "clip": "clips/02.mp4" },
    { "type": "feature", "clip": "clips/03.mp4" },
    { "type": "feature", "clip": "clips/04.mp4" },
    { "type": "cta",     "clip": "clips/05.mp4" }
  ]
}
```

씬 길이는 `src/timing.ts`가 자동 계산한다. **직접 고칠 필요 없다.**
`씬길이 = ceil((나레이션초 × 30 + (씬수−1) × 15) ÷ 씬수)` 프레임

## 7단계 — 렌더

```
cd remotion-project
npm install          # 최초 1회만
npm run render:data
```

→ `remotion-project/out/shorts.mp4`

`--browser-executable` 옵션은 **로컬에서 필요 없다.** (클라우드 환경 우회용이었음)

**`Cannot read file ...: The cloud operation was not completed` 로 죽으면 OneDrive 문제다.**
이 폴더가 OneDrive 안에 있으면 파일이 아직 안 내려와서 빌드가 실패한다.
한 번 더 실행하면 대개 되고, 계속 실패하면 폴더째 `C:\shorts` 같은 로컬 경로로
옮기라고 안내한다.

## 8단계 — 검수 (생략 금지)

```
node tools/qc.js
```

자막이 뜬 직후(+0.45초) 프레임을 뽑아 가로로 붙인 `work/qc/row*.jpg`를 만든다.
**이 이미지를 직접 열어보고** 자막과 화면이 맞는지 확인한다.

- 자막과 화면이 어긋나면 → **대본이 아니라 씬 순서를 바꾸는 게 빠르다.** `cuts.json`에서 씬을 맞바꾼다.
- 워터마크가 남아 있으면 → 2단계로 돌아가 crop을 다시 실측한다.

고친 뒤에는 5→7→8을 다시 돌린다.

---

## 마무리 안내 (사용자에게 반드시 전달)

- `product.json`의 `coupangUrl`을 실제 파트너스 링크로 교체했는지 확인
- 업로드 캡션에 **"쿠팡 파트너스 활동으로 일정액의 수수료를 제공받습니다"** 문구 필수 (미표기 시 제재 대상)
- 업로드 캡션에 "프로필 링크" 안내 문구 넣기
- **저작권**: 남의 틱톡/더우인 영상을 그대로 쓰는 것은 리스크가 있으며 본인 부담이다.
  판매사가 배포용으로 제공한 소재가 상대적으로 안전하다. 이 점을 매번 고지한다.

## BGM

`remotion-project/public/` 아래에 파일을 넣고 `product.json`의 `bgm`에 경로를 쓴다
(예: `"bgm": "audio/bgm.mp3"`). 볼륨은 0.18로 고정되어 나레이션을 가리지 않는다.

## 참고 자료

- `references/실전사례-주방기름때.md` — 실제 제작 기록. 소재 선별, 워터마크 좌표 실측,
  씬 순서를 갈아엎은 과정이 그대로 적혀 있다. 막히면 이걸 먼저 본다.
