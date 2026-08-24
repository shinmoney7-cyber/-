# shopping-shorts-sync

쿠팡 상품 URL로부터 쿠팡파트너스 제휴 딥링크를 자동 생성하고, 그 결과를 인포크
(Inpock) 링크 카드에 자동 반영하는 도구.

- https://link.inpock.co.kr/harujin
- https://link.inpock.co.kr/shinjh

## 현재 상태 / 중요 제약

- 쿠팡파트너스 API 키는 아직 발급 전이다. 키가 없어도 `COUPANG_API_MODE=mock`(기본값)으로
  전체 파이프라인을 드라이런할 수 있다.
- 인포크에는 공개 API가 없어 브라우저 자동화(Playwright)로 링크 카드를 등록/수정한다.
  이 프로젝트를 만든 환경에서는 `link.inpock.co.kr` 접속이 네트워크 정책으로 막혀 있어서
  실제 로그인/편집기 화면의 DOM을 확인하지 못했다. **실제 계정으로 처음 실행하기 전에
  반드시 [docs/CALIBRATION.md](docs/CALIBRATION.md)를 먼저 따라 셀렉터를 보정할 것.**

## 설치

```bash
pip install -r requirements.txt
cp .env.example .env   # 값 채우기
```

Playwright는 `playwright install`을 실행하지 않는다 — `.env`의
`PLAYWRIGHT_CHROMIUM_PATH`가 가리키는, 이미 설치된 Chromium을 사용한다.

## 사용법

```bash
# 상품 목록 -> 쿠팡파트너스 딥링크 생성 (기본은 mock 모드)
python -m shopping_shorts_sync deeplink generate --input data/products.example.json

# 인포크 페이지에 링크 카드 동기화 (dry-run: 브라우저 없이 시뮬레이션)
python -m shopping_shorts_sync inpock sync --input data/products.example.json --dry-run

# 전체 파이프라인 (쿠팡 딥링크 생성 + 인포크 동기화)
python -m shopping_shorts_sync sync all --input data/products.example.json --dry-run

# 저장된 동기화 상태 확인/초기화
python -m shopping_shorts_sync state show
python -m shopping_shorts_sync state reset --product-id harujin-vacuum-01
```

`--dry-run`을 빼고 `COUPANG_API_MODE=live` + 실제 키, 그리고 인포크 계정 정보를 채우면
실제로 동작한다 (단, 위 CALIBRATION 절차를 먼저 거친 뒤).

## 상품 검색 + 쿠팡 자동매칭

네이버 쇼핑(공식 API)·다이소몰·올리브영(RPA)에서 키워드로 검색해서 상품명/이미지를
보여주고, 그중 하나를 고르면 **쿠팡닷컴을 이름으로 검색해서 상위 1개 결과를 자동으로
매칭**해 `products.json`에 새 상품으로 추가한다. 쿠팡파트너스 API에는 이름 검색 기능이
없어서(딥링크 API는 이미 아는 URL을 변환만 함) 이 매칭도 RPA로 한다 — 이름 유사도
기반이라 가끔 다른 상품이 걸릴 수 있음을 감안하고 오너가 자동 적용을 선택했다.

```bash
# 3개 소스에서 키워드로 검색 (dry-run: 목 데이터, 네트워크/브라우저 불필요)
python -m shopping_shorts_sync search run --keyword "무선 청소기" --dry-run

# 결과 중 하나를 골라 쿠팡 매칭 -> products.json에 자동 upsert("연동")
python -m shopping_shorts_sync search match --keyword "무선 청소기" \
  --source daiso --index 0 --target-page harujin --category 생활용품 \
  --input data/products.example.json --dry-run
```

다이소몰/올리브영 RPA와 쿠팡 이름-매칭 RPA 모두 `docs/CALIBRATION.md`의 셀렉터 보정이
끝나기 전까지는 `--dry-run`으로만 쓸 것.

## 대본 자동생성 (AIDA + 7가지 설득요소)

상품마다 AIDA(주의-흥미-욕망-행동) 구조의 대본 후보를 **정확히 5개** 자동 생성해서
`data/scripts/<product_id>.json`에 저장한다. 욕망(D) 단계는 7가지 설득요소 중
카테고리에 맞는 5개를 하나씩 적용한다: 욕망 그 자체(base), 손실회피, 사회적 증거,
권위/전문가 인용, 호기심 갭, 이득의 수치화, 가족 서사. 카테고리는 뷰티/생활용품/
육아/다이어트/가전을 지원하며 각 카테고리별 타겟 욕망 리스트를 내장하고 있다
(`src/shopping_shorts_sync/scriptgen.py`). 같은 상품명+카테고리는 항상 같은 5개를
만드는 결정적(deterministic) 템플릿 생성기라, 이미 하나를 선택한 상태에서 재생성해도
후보 내용이 갑자기 바뀌어 놀랄 일이 없다.

```bash
# 상품명/카테고리로 대본 5개 자동 생성
python -m shopping_shorts_sync script generate --product-id harujin-vacuum-01 \
  --name "무선 청소기 XYZ" --category 가전

# 상품의 5개 대본 후보 확인
python -m shopping_shorts_sync script show --product-id harujin-vacuum-01

# 하나를 선택 -> 즉시 data/state.json에 자동 반영("연동")
python -m shopping_shorts_sync script select --product-id harujin-vacuum-01 \
  --candidate-id 3 --input data/products.example.json

# 플랫폼별 해시태그 + 쿠팡파트너스 고지문구 + [광고] 표기 안내
python -m shopping_shorts_sync script hashtags --name "무선 청소기 XYZ" --category 가전
```

생성된 후보는 평범한 JSON 파일(`data/scripts/*.json`)이라 직접 열어서 손으로 다듬어도
된다. 손으로 다듬은 뒤 `script generate`를 다시 돌리면 덮어쓰므로, 재생성하려면
`--force`를 명시해야 한다. 이미지(`products.json`의 `thumbnail`)도 마찬가지로 직접
수정 가능.

### 표기 규칙 (필수)

- **`[광고]`**: 영상 화면 우측 상단에 항상 삽입 (owner 규칙, `scriptgen.AD_LABEL`).
- **쿠팡 파트너스 고지문구**: "이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른
  일정액의 수수료를 제공받습니다." — 설명란/본문에 항상 표기 (`scriptgen.COUPANG_PARTNERS_DISCLOSURE`).

두 가지 모두 `script generate`, `script hashtags`, `pipeline new-product` 실행 시
콘솔에 리마인더로 출력되고, 웹 대시보드의 상품/해시태그/승인 단계 화면에도 항상
표시된다.

## 한 번에: 검색 -> 쿠팡 자동매칭 -> 대본 자동생성 -> 딥링크

`pipeline new-product`는 검색 결과 선택 하나로 나머지 세 단계(쿠팡 이름-매칭 자동
연동, AIDA 대본 5개 자동생성, 쿠팡파트너스 딥링크 실제 생성)를 이어서 처리한다.

```bash
python -m shopping_shorts_sync pipeline new-product --keyword "무선 청소기" \
  --source daiso --index 0 --target-page harujin --category 생활용품 \
  --input data/products.example.json --dry-run
```

## 웹 대시보드 (모바일 대응)

검색 -> 상품 선택(쿠팡 자동연동 + 대본 자동생성) -> 대본 선택 -> 플랫폼별 해시태그
-> 최종 확인("확인키") 승인까지 이어지는 모바일 반응형 웹 대시보드. CLI가 쓰는
동일한 함수를 그대로 호출하므로 로직은 하나뿐이다.

```bash
python -m shopping_shorts_sync web --input data/products.example.json --port 5000
```

브라우저에서 `http://127.0.0.1:5000` 접속. 화면 구성:

1. **대시보드**: 등록된 상품 목록 + 쿠팡링크/대본선택/승인 상태 배지
2. **상품 검색**: 네이버쇼핑/다이소몰/올리브영에서 검색 -> 5개씩 총 15개 그리드 ->
   하나 선택 시 쿠팡 자동매칭 + 대본 5개 자동생성 + 딥링크 생성이 한 번에 실행
3. **상품 상세** (탭형 6단계, 각 단계에 이전/다음 내비게이션):
   - 1) 상품정보 (썸네일, 쿠팡 딥링크, `[광고]` 표기 리마인더)
   - 2) 영상선택 (유튜브+인스타그램에서 관련 영상 최대 15개, 3개 선택 -> 자동
     짜깁기 미리보기)
   - 3) 대본선택 (AIDA 5개 후보, 설득요소 태그, 선택/재생성)
   - 4) 음성생성 (타입캐스트 20개 보이스 카탈로그, 선택 즉시 생성)
   - 5) 해시태그/배포 (인스타그램·쓰레드·유튜브·틱톡·네이버클립·토스·당근마켓·
     네이버블로그별 해시태그, 쿠팡파트너스 고지문구)
   - 6) 최종승인 (썸네일+대본 완성본을 함께 보고 "확인키" 승인 -> 인포크 자동 반영)

## 배포 (Render)

몇 명이 실제로 계속 쓰는 용도라, 재배포/재시작에도 데이터(등록 상품, 대본 선택,
쿠팡 링크, 승인 상태)가 남아있도록 **Render Starter 플랜 + Persistent Disk**로
배포하는 걸 기준으로 잡았다 (무료 플랜은 디스크가 임시라 재배포·휴면 후 기상 시
데이터가 초기화된다). 접근 제한(Basic Auth 등)은 걸지 않았다 — 링크만 알면 누구나
들어올 수 있다.

`render.yaml`이 이미 이 구성을 담고 있다: `/var/data`에 1GB Persistent Disk를
마운트하고 `PRODUCTS_PATH`/`STATE_FILE_PATH`/`SCRIPTS_DIR`를 전부 그 아래로
잡아뒀다 (저장소 안의 `data/`가 아니라 디스크 쪽에 쓰기 때문에 배포/재시작에도
안전).

**처음 배포하는 방법** (Render 계정 로그인은 사용자가 직접 해야 함 — 계정 생성/GitHub
연동은 이 세션에서 대신 해줄 수 없다):

1. https://dashboard.render.com 에서 로그인 (없으면 GitHub 계정으로 가입)
2. **New +** -> **Blueprint** 선택
3. 이 GitHub 저장소(`shinmoney7-cyber/-`)를 연결 -> Render가 `render.yaml`을
   자동으로 읽어서 서비스 구성을 미리 보여준다
4. 그대로 **Apply** 클릭 -> 빌드 후 몇 분 뒤 `https://shopping-shorts-sync.onrender.com`
   같은 형태의 주소가 발급된다 (실제 URL은 이름이 겹치면 뒤에 숫자가 붙을 수 있음)
5. 쿠팡/네이버/유튜브/타입캐스트 실제 키가 있으면 Render 대시보드 -> 서비스 ->
   **Environment** 탭에서 값 입력 + `COUPANG_API_MODE`/`TYPECAST_MODE`를
   `live`로 변경 (이 값들은 `render.yaml`에 커밋되어 있지 않다 — `sync: false`)

배포가 끝나면 그 주소가 곧 "홈페이지 주소"이며, 별도 도메인 연결 없이 그 URL을
그대로 몇 명에게 공유하면 된다.

## 영상 소재 검색 ("2차 창작") — 유튜브 · 인스타그램

틱톡/도우인/샤오훙슈는 제품 키워드로 영상을 검색해오는 공개 API가 없다. 대신
**이용하기 쉬운 순서대로** 두 개의 실제 공식 API를 붙였다:

1. **유튜브** (Data API v3) — API 키 발급만으로 바로 사용, 심사 없음. 가장 쉬움.
2. **인스타그램** (Graph API 해시태그 검색) — 공식 API지만 비즈니스/크리에이터
   계정 전환 + 페이스북 페이지 연결 + Meta 앱 심사가 필요해서 유튜브보다 훨씬
   진입장벽이 높다 (`docs/CALIBRATION.md` 참고).

`search`/`pipeline`의 `--source` 옵션에 둘 다 추가되어 네이버/다이소/올리브영과
동일하게 다룬다 — 검색 결과(영상 제목/썸네일/링크)를 "2차 창작"(리뷰 요약, 정보성
편집 등) 소재로 쓰고, 영상 제목을 쿠팡 이름-매칭에 그대로 활용한다.

```bash
python -m shopping_shorts_sync search run --keyword "무선 청소기" --source youtube --dry-run
python -m shopping_shorts_sync search run --keyword "무선 청소기" --source instagram --dry-run
```

`YOUTUBE_API_KEY`/`INSTAGRAM_ACCESS_TOKEN`+`INSTAGRAM_IG_USER_ID` 없이는
`--dry-run`(mock)만 가능.

## 영상 자동 짜깁기

웹 대시보드 2단계("영상선택")에서 유튜브+인스타그램 검색 결과 중 정확히 3개를
고르면, `yt-dlp`로 다운로드 후 각 클립을 `VIDEO_CLIP_SECONDS`초(기본 5초)만 잘라
`ffmpeg`로 이어붙인 미리보기 영상 1개를 만든다.

```bash
python -m shopping_shorts_sync video stitch --product-id harujin-vacuum-01 \
  --url "https://www.youtube.com/watch?v=aaa" \
  --url "https://www.youtube.com/watch?v=bbb" \
  --url "https://www.instagram.com/p/ccc/" \
  --dry-run
```

`--dry-run`(기본값)은 yt-dlp/ffmpeg 없이도 동작 (더미 파일로 파이프라인만 검증).
`--live`는 `yt-dlp`/`ffmpeg`가 PATH에 있어야 하고, 실제 영상 파일로는 테스트해보지
못했으니 `docs/CALIBRATION.md`를 먼저 볼 것. **남의 영상을 다운로드해서 재사용하는
것 자체는 저작권/2차 창작 관련 판단 영역이며, 이 도구는 기계적인 다운로드·합치기만
담당한다** — 그 판단은 오너 본인의 몫이다.

## 음성 생성 (Typecast TTS)

캡컷은 외부에서 호출 가능한 공개 API가 없어서, 대신 공개 API가 있는 **타입캐스트
(Typecast)**로 대본 음성을 생성한다. 보이스는 20종 카탈로그
(`src/shopping_shorts_sync/tts/voices.py`) — 표준 + 경상도/전라도/충청도/강원도
사투리 x 남/여 x 20-30대/40-60대. 이 중 "예슬"(표준_여성_20-30대)만 실제로 확인된
보이스이고 나머지 19개는 자리표시자이니 실전 연동 전 `docs/CALIBRATION.md`를 먼저
볼 것.

```bash
# 카탈로그 확인
python -m shopping_shorts_sync tts voices

# 대본 선택 후("script select") 음성 생성 -> data/state.json에 자동 반영
python -m shopping_shorts_sync tts generate --product-id harujin-vacuum-01 \
  --voice-label 표준_여성_20-30대
```

웹 대시보드에서는 2단계(대본선택) 다음이 바로 3단계(음성생성)라, 대본을 고르면
"음성으로 바로 다음 자동연동"(오너 요구사항) 흐름 그대로 이어진다.

## 발행 (TikTok / YouTube / Instagram)

영상 짜깁기(`video stitch`)와 대본 선택(`script select`)이 끝난 상품은 각
플랫폼 공식 API로 바로 발행할 수 있다. 기본은 `--dry-run`(API 호출 없이
결과만 기록)이고, `--live`로 실제 게시된다 — 셋 다 앱 리뷰/OAuth 동의/공개
URL 등 사전 준비가 필요하니 `docs/CALIBRATION.md`의 "발행(퍼블리싱) 절차"를
먼저 볼 것.

```bash
# dry-run (기본): API 호출 없이 상태만 기록
python -m shopping_shorts_sync publish run --product-id harujin-vacuum-01 --platform tiktok

# 실전 연동
python -m shopping_shorts_sync publish run --product-id harujin-vacuum-01 \
  --platform youtube --live
```

웹 대시보드 5단계("해시태그/배포")에서는 8개 플랫폼 해시태그 중 틱톡/유튜브/
인스타그램 3개에만 "지금 발행" 버튼이 노출된다(나머지 5개는 여전히 해시태그
안내만 제공하는 수동 게시 전제). 인스타그램은 로컬 영상 경로를 그대로 못 쓰고
공개 HTTPS URL이 필요해서, `PUBLIC_BASE_URL`(배포된 웹앱의 base URL)이
설정돼 있어야 `--live` 발행이 가능하다.

## 인포크 자동 반영

두 인포크 계정(`https://link.inpock.co.kr/harujin`, `.../shinjh`)은 대시보드
상단에 항상 링크로 노출된다. 웹 대시보드 6단계("최종승인")에서 "확인키" 승인을
누르는 순간, 그 상품의 `target_page`(harujin/shinjh)에 맞는 인포크 링크 카드에
자동으로 반영된다(`run_inpock_stage` 재사용, 기본은 mock). 실전 연동은 승인 폼의
"실전 연동" 체크박스 + 인포크 로그인 정보(`INPOCK_EMAIL`/`INPOCK_PASSWORD`)가
필요하고, `docs/CALIBRATION.md`의 셀렉터 보정이 먼저다.

## 현재 스코프에 포함되지 않은 것

이 프로젝트는 실제로 동작하는 부분(쿠팡파트너스 딥링크 API, 상품명 자동 매칭,
대본 자동생성, 유튜브/인스타그램 검색, 영상 다운로드+자동짜깁기, 타입캐스트 TTS,
인포크 RPA 동기화)과 현실적으로 불가능한 부분을 명확히 구분한다. **틱톡/도우인/
샤오훙슈에서의 실시간 영상 검색**은 여전히 이 저장소에 구현되어 있지 않다 —
세 플랫폼 모두 키워드로 영상을 검색해오는 공개 API 자체가 없다(도우인/샤오훙슈는
접근 자체가 막혀 있고, 틱톡 공식 API는 리서치용이라 이 용도로 못 씀).

## 입력 파일 형식

`data/products.example.json` / `data/products.example.csv` 참고. 각 상품은
`id`(생략 시 쿠팡 URL 기반 해시로 자동 생성), `name`, `coupang_url`, `thumbnail`(이미지
URL), `category`, `target_page`(`harujin` 또는 `shinjh`), `enabled` 필드를 가진다.

## 상태/멱등성

`data/state.json`(git-ignore 대상)에 상품별 생성된 딥링크와 마지막 동기화 시점, 필드
해시를 기록한다. 같은 입력으로 재실행해도 변경된 상품만 다시 처리하고, 이미 동기화된
상품은 건너뛴다.

## 테스트

```bash
pytest
```

모든 테스트는 목(mock) 기반이라 네트워크 접근 없이 통과해야 한다. `test_inpock_rpa.py`,
`test_search_rpa.py`는 각각 `fixtures/inpock_fixture_site/`,
`fixtures/{daiso,oliveyoung,coupang}_fixture_site/`의 가짜 페이지를 사용하는
**구조 테스트**이며, 실제 사이트를 검증하지 않는다.
