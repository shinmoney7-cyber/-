# 셀렉터 보정 가이드

이 프로젝트를 만든 세션의 네트워크 정책이 `link.inpock.co.kr`, `daisomall.co.kr`,
`oliveyoung.co.kr`, `coupang.com`, `openapi.naver.com` **전부** 접속을 차단하고 있었다
(프록시 단계에서 CONNECT가 403으로 거부됨 — 조직 egress 정책, 우회 불가). 그래서 아래
모든 셀렉터/엔드포인트는 **실제 사이트를 한 번도 열어보지 못한 채** 작성되었다. 실제
사이트에 접근 가능한 환경(사용자 PC, 또는 네트워크 정책이 다른 세션)에서 실행하기 전에
반드시 아래 절차를 거칠 것.

## Inpock 절차

1. **로그인 방식 재확인**: 이메일/비밀번호만으로 로그인되는지, 중간에 예상 못 한 팝업(약관
   동의, 보안 확인 등)이 뜨지 않는지 브라우저로 직접 로그인하며 확인한다.
2. **개발자 도구(F12)를 켠 채로** https://link.inpock.co.kr 에 직접 로그인해서, 실제
   로그인 폼의 input/button 셀렉터를 확인하고 `selectors.py`의 `LoginSelectors` 안 모든
   `# TODO CALIBRATE` 항목을 실제 값으로 교체한다.
3. 로그인 후 harujin/shinjh 페이지 전환 방법(URL 패턴인지, 페이지 내 스위처 버튼인지)을
   확인하고 `PAGE_SWITCH_URL_TEMPLATE` 또는 관련 상수를 갱신한다.
4. 링크 카드 편집기로 들어가서 "링크 추가", 제목/URL/썸네일 입력 필드, 저장 버튼의 실제
   셀렉터를 확인하고 `EditorSelectors`를 갱신한다. 기존 카드 목록에서 카드 하나를 특정하는
   방법(제목 매칭이 안전한지, data-testid 같은 안정적인 속성이 있는지)도 함께 확인한다.
5. 셀렉터를 갱신한 뒤 `pytest tests/test_inpock_rpa.py`를 다시 돌려 구조적으로 깨진 게
   없는지 회귀 확인한다 (이 테스트는 `fixtures/inpock_fixture_site/`의 가짜 페이지를 쓰므로,
   필요하면 그 가짜 페이지도 실제 구조에 맞게 함께 갱신한다).
6. 실제 사이트에 대해 처음 실행할 때는 반드시:
   - `--headed --dry-run` 으로 실행해서 브라우저 창을 눈으로 보면서 각 스텝이 의도대로
     동작하는지 확인
   - 실패 시 `debug/`에 저장되는 스크린샷을 확인
   - 문제 없음을 확인한 뒤에만 `--live`로 실제 카드 생성/수정을 실행한다

## 검색/매칭 절차 (다이소·올리브영·쿠팡)

`src/shopping_shorts_sync/search/selectors.py`의 `DaisoSelectors`,
`OliveYoungSelectors`, `CoupangSearchSelectors`도 전부 미검증 추정치다.

1. 각 사이트에서 실제로 검색했을 때의 URL 패턴을 확인하고 `SEARCH_URL_TEMPLATE`을
   갱신한다 (쿼리 파라미터 이름이 다를 수 있음).
2. 검색 결과 페이지에서 상품 카드 하나의 실제 구조(감싸는 엘리먼트, 이름/이미지/링크/가격
   각각의 셀렉터)를 확인하고 갱신한다.
3. 다이소몰/올리브영/쿠팡 모두 **로그인 없이** 검색 결과가 보이는지 확인 — 만약 로그인이
   필요하거나 캡차/봇 차단이 있으면 RPA 자동화 자체가 어려워질 수 있으니 가장 먼저 확인.
4. 갱신 후 `pytest tests/test_search_rpa.py`로 구조 회귀 확인 (필요하면
   `fixtures/{daiso,oliveyoung,coupang}_fixture_site/`의 가짜 페이지도 실제 구조에 맞게
   갱신).
5. 네이버는 공식 API라 셀렉터는 없지만, `NAVER_CLIENT_ID`/`NAVER_CLIENT_SECRET` 발급 후
   실제 응답 스펙(`items[].title`에 `<b>` 태그가 포함되는지, `image`/`lprice` 필드명 등)이
   `search/naver.py`의 가정과 맞는지 실제 호출로 한 번 확인할 것.
6. 쿠팡 이름-매칭은 상위 1개 결과를 사람 확인 없이 자동 적용하는 것으로 정했다(오너 확인).
   실제로 틀린 매칭이 자주 나오면 상위 몇 개를 보여주고 확인받는 방식으로 바꾸는 걸
   고려할 것.

## YouTube 검색 절차

`src/shopping_shorts_sync/search/youtube.py`는 공식 YouTube Data API v3
(`search.list`)를 쓰므로 셀렉터 보정은 필요 없지만, 이 환경은
`googleapis.com` 접속이 막혀 있어 실제 응답 스펙을 확인하지 못했다.

1. `YOUTUBE_API_KEY` 발급 후 (Google Cloud Console -> YouTube Data API v3
   사용 설정 -> API 키 생성) 실제 호출 1회로 `items[].id.videoId`,
   `items[].snippet.title/thumbnails.high.url` 필드명이 맞는지 확인.
2. 쿼터 제한(기본 일일 10,000 유닛, `search.list` 1회당 100 유닛)이
   운영 물량에 충분한지 확인.

## Typecast TTS 절차

`src/shopping_shorts_sync/tts/typecast_client.py`의 엔드포인트/응답 스키마는
Typecast 공개 문서 기반 추정치이며, `typecast.ai` 접속이 막혀 있어 실제로
호출해보지 못했다. **`--live`로 처음 실행하기 전 반드시:**

1. `TYPECAST_API_KEY` 발급 후 실제 `POST /api/speak` 호출 1회로 요청 바디
   필드명(`text`/`lang`/`actor_id`/`speed_x`)과 응답 구조(동기 응답인지,
   `speak_v2_url`로 폴링해야 하는지)가 맞는지 확인하고 다르면
   `typecast_client.py`의 `SPEAK_ENDPOINT`/파싱 로직을 갱신.
2. `src/shopping_shorts_sync/tts/voices.py`의 `VOICE_CATALOG` 중
   `예슬`(표준_여성_20-30대) 외 19개는 전부 `TODO_CALIBRATE_*` 자리표시자다.
   Typecast 대시보드에서 실제 배우 목록을 확인해서 경상도/전라도/충청도/
   강원도 사투리 및 남성 보이스에 맞는 실제 `actor_id`로 교체할 것.
3. 사투리 보이스가 실제로 사투리 억양을 지원하는지, 아니면 표준어 억양에
   텍스트만 사투리 표현으로 대체하는 방식인지 확인 (대본 자체에 사투리
   표현을 넣을지, TTS 엔진에 맡길지의 갈림길).

## Instagram 검색 절차

`src/shopping_shorts_sync/search/instagram.py`는 Instagram Graph API의
해시태그 검색(`ig_hashtag_search` -> `{hashtag_id}/top_media`)을 쓴다.
`graph.facebook.com` 접속이 막혀 있어 실제로 호출해보지 못했다.
**유튜브보다 진입장벽이 훨씬 높다 -- `--live` 전 반드시 아래를 순서대로:**

1. Instagram 계정을 **비즈니스 또는 크리에이터 계정**으로 전환하고
   페이스북 페이지에 연결 (개인 계정으로는 이 API 자체를 못 씀).
2. Meta for Developers에서 앱 생성 -> `instagram_basic` 권한 요청 ->
   **App Review** 통과 전까지는 앱 소유자 본인 계정으로만 테스트 가능.
3. `INSTAGRAM_ACCESS_TOKEN`(장기 토큰), `INSTAGRAM_IG_USER_ID` 발급 후
   실제 호출 1회로 `data[].id`, `top_media`의
   `media_type`/`media_url`/`thumbnail_url`/`permalink` 필드명이 맞는지 확인.
4. 해시태그 검색은 **7일 롤링 기준 30개 해시태그**로 제한된다 -- 운영
   물량(하루에 몇 개 상품을 처리할지)이 이 한도 안에 들어오는지 확인.
5. 검색어(제품명)에 공백을 제거해 해시태그로 변환하는 지금 방식
   (`search/instagram.py`의 `keyword.replace(" ", "")`)이 실제로 의미 있는
   해시태그를 찾아내는지 확인 -- 안 되면 카테고리별 대표 해시태그 매핑표를
   따로 만드는 걸 고려할 것.

## 영상 다운로드 + 자동 짜깁기 절차

`src/shopping_shorts_sync/video/downloader.py`(yt-dlp)와
`stitcher.py`(ffmpeg)는 실제 영상 파일로 한 번도 테스트해보지 못했다
(이 환경에 소스로 쓸 실제 영상을 내려받을 네트워크가 없음).
**`--live` 전 반드시:**

1. `yt-dlp`, `ffmpeg`를 설치하고 PATH에 있는지 확인 (`YTDLP_PATH`/
   `FFMPEG_PATH`로 다른 경로 지정 가능).
2. 유튜브 영상 URL 1개로 `video stitch`를 3개 URL(같은 영상 반복해도 됨)로
   실행해보고, 실제로 `stitched.mp4`가 재생 가능한 파일로 나오는지 확인.
3. 인스타그램 릴스/영상 URL도 yt-dlp가 다운로드 가능한지 별도 확인 (사이트별
   지원 여부가 yt-dlp 버전에 따라 달라짐).
4. 지금은 각 클립의 **처음 `VIDEO_CLIP_SECONDS`초만** 잘라서 이어붙인다 --
   실제로 써보고 이 방식(처음부터 자르기)이 부자연스러우면 클립마다 하이라이트
   구간을 고르는 기능으로 발전시킬 것.
5. **다운로드한 영상을 재사용하는 것 자체가 저작권/각 플랫폼 약관 판단
   영역이다** -- 이 도구는 기계적인 다운로드/합치기만 담당하고, 그 판단은
   오너 본인의 몫이라는 전제로 만들어졌다.

## 발행(퍼블리싱) 절차

`src/shopping_shorts_sync/publisher/`의 `tiktok.py`/`youtube.py`/
`instagram.py`는 각 플랫폼의 공식 API를 쓰지만, 이 환경은
`open.tiktokapis.com`/`googleapis.com`/`graph.facebook.com` 접속이 모두
막혀 있어 실제로 한 번도 호출해보지 못했다. `publish run`(CLI)과 대시보드
5단계의 "지금 발행" 버튼은 기본이 `--dry-run`(체크박스 미체크)이라 API 키
없이도 흐름 확인이 가능하지만, **`--live`(실전 연동)로 처음 실행하기 전
반드시 아래를 플랫폼별로 확인할 것.**

### TikTok

1. TikTok for Developers에서 앱 생성 -> Content Posting API 스코프 신청.
   **App Review 통과 전에는 개발자 본인 테스트 계정으로만 게시 가능** --
   운영 계정으로 쓰려면 리뷰 통과가 먼저.
2. `TIKTOK_ACCESS_TOKEN` 발급 후 실제 `init` 호출 1회로 응답 구조
   (`data.publish_id`/`data.upload_url`, 에러 시 `error.code`/`error.message`
   필드명)가 `tiktok.py`의 가정과 맞는지 확인.
3. 청크 업로드(`PUT` + `Content-Range` 헤더)가 실제로 10MiB 단위로
   맞는지, 혹은 TikTok 쪽 권장 청크 크기가 다른지 확인.

### YouTube

1. Google Cloud Console에서 OAuth 클라이언트(데스크톱 앱 유형)를 만들고
   `client_secret.json`을 내려받아 `YOUTUBE_CLIENT_SECRETS_FILE` 경로에
   둔다.
2. **OAuth 동의 화면은 브라우저가 없는 서버(Render 등)에서 직접 열 수
   없다** -- 로컬 PC에서 `publish run --platform youtube --live` (또는
   동일 자격증명으로 `YouTubePublisher._get_credentials()`)를 한 번
   실행해 브라우저 동의를 마치고, 그 결과로 생성되는 토큰 파일
   (`YOUTUBE_TOKEN_FILE`, 기본 `data/youtube_token.json`)을 서버의 같은
   경로에 그대로 올려서 재사용한다. Render라면 영구 디스크
   (`/var/data/youtube_token.json`)에 올려두면 재배포에도 유지된다.
3. 업로드 성공 후 `response.id`/`snippet`/`status` 필드명이
   `youtube.py`의 가정과 맞는지, 쇼츠로 인식되려면 세로 영상 + 60초 이하
   조건이 실제로 충족되는지 확인.

### Instagram

1. `search/instagram.py`용 계정 설정에 더해 **`instagram_content_publish`
   권한**까지 App Review에서 승인받아야 게시가 된다 (검색 절차의
   `instagram_basic`보다 진입장벽이 높음).
2. **로컬 파일 경로를 그대로 못 쓴다** -- Instagram Graph API는 영상
   컨테이너를 만들 때 공개 HTTPS URL을 요구한다. `PUBLIC_BASE_URL`을
   배포된 웹앱의 실제 base URL로 설정하면 `publish run`/대시보드가
   기존 `/videos/<product_id>/<filename>` 라우트(webapp에 이미 있음)로
   URL을 자동 구성한다 -- 즉 웹앱이 실제로 배포되어 있어야 `--live`
   Instagram 발행이 가능하다. 로컬에서만 테스트할 때는 `--video-url`로
   ngrok 등 임시 공개 URL을 직접 넘길 것.
3. 컨테이너 생성 -> `status_code` 폴링(`FINISHED`/`ERROR`) -> `media_publish`
   흐름이 실제 응답과 맞는지, 폴링 간격(`_POLL_INTERVAL_S`=5초)·최대
   횟수(`_POLL_MAX_ATTEMPTS`=24회, 총 2분)가 실제 처리 시간에 충분한지
   확인.

## 키워드 트렌드 조회 절차

`src/shopping_shorts_sync/trend/naver_ad.py`는 네이버 검색광고(SearchAd)
API의 키워드 도구(`/keywordstool`)를 쓴다. 이 개발 환경은 실제 API
호스트 접속이 막혀 있어서 여기선 한 번도 호출해볼 수 없었지만,
**Render에 배포한 실제 서비스에서 `--live`로 검증 완료** -- 아래 내용은
전부 실제 응답으로 확인된 사실이다.

1. **API 키 발급**: searchad.naver.com(=ads.naver.com) 가입(광고주 등록,
   무료) -> 로그인 후 좌측 메뉴 **SA API 사용 관리** -> API 사용 신청 ->
   발급되는 세 값(화면 상단의 CUSTOMER_ID, 엑세스라이선스, 비밀키)을
   각각 `NAVER_AD_CUSTOMER_ID`/`NAVER_AD_API_KEY`/`NAVER_AD_SECRET_KEY`에
   설정. 비밀키는 발급 시 한 번만 표시되니 바로 복사해둘 것.
2. **호스트는 `api.searchad.naver.com`** (구 문서에 나오는
   `api.naver.com`으로 요청해도 여기로 301 리다이렉트된다) --
   `naver_ad.py`의 `API_HOST`가 이미 이 값으로 되어 있음.
3. `signing.py`의 서명 대상 문자열(`f"{timestamp}.{method}.{uri}"`,
   `uri`는 쿼리스트링 없는 경로만, 비밀키는 base64 디코딩하지 않고 그냥
   UTF-8 문자열 바이트로 HMAC-SHA256 후 base64)과 헤더 이름
   (`X-Timestamp`/`X-API-KEY`/`X-Customer`/`X-Signature`)이 실제로
   `status:200`을 받는 조합임을 확인함.
4. **자주 겪는 함정 (직접 겪음)**: Render 등 대시보드의 환경변수
   입력창에 값을 붙여넣을 때 기존 값을 먼저 지우지 않으면 두 값이
   이어붙어 저장된다 (예: 74자짜리 키가 148자가 됨). 이러면 API가
   `403 Invalid Signature`를 반환하는데, 서명 계산 로직 문제로 착각하기
   쉽다 -- 값을 바꿀 땐 항상 입력칸 전체 선택(Ctrl+A) 후 지우고
   붙여넣을 것. 길이가 예상과 다르면 이 문제부터 의심.
5. `naver_ad.py`가 가정하는 응답 필드명(`keywordList`, `relKeyword`,
   `monthlyPcQcCnt`, `monthlyMobileQcCnt`, `compIdx`)은 실제 응답과
   일치함 (예: `{"keywordList":[{"relKeyword":"...","monthlyPcQcCnt":2790,
   "monthlyMobileQcCnt":12000,"compIdx":"중간",...}]}`). 저검색량 키워드가
   숫자 대신 `"< 10"` 문자열로 오는 것까지는 아직 실제로 못 봄 --
   `_parse_count`의 그 부분만 미확인 상태로 남음.
6. **`hintKeywords`는 공백이 있으면 400을 반환한다** (`{"code":11001,
   "message":"hintKeywords 파라미터가 유효하지 않습니다."}`, 확인됨) --
   "무타공 수납장" 같은 띄어쓰기 있는 구는 "무타공수납장"처럼 붙여서
   보내야 한다. `naver_ad.py`의 `search()`가 이미 공백을 제거하고
   보낸다. 한 번에 넘길 수 있는 최대 개수(현재 5개로 가정)는 아직
   미확인.
7. **전월 대비 증가율**은 네이버 API 자체가 주지 않는 값이라
   `history_store.py`가 매 조회마다 `TREND_HISTORY_PATH`(기본
   `data/trend_history.json`)에 이번 달 합계를 누적 저장해서 계산한다
   -- 즉 같은 키워드를 두 번째 달에 조회해야 값이 뜨고, 첫 조회는 항상
   "첫 조회"로 표시된다.

## 확인이 필요한 열린 질문

- 쿠팡파트너스 API의 정확한 HMAC 서명 포맷(헤더 이름, 날짜 포맷, 서명 대상 문자열에 쿼리
  스트링 포함 여부)은 실제 API 키 발급 후 공식 문서로 재확인 필요
- 쿠팡 딥링크 API 1회 호출당 최대 URL 개수/레이트 리밋
- 인포크 링크 카드 수정 시 카드 순서(정렬)까지 유지해야 하는지, 아니면 필드 교체만으로
  충분한지
- 다이소몰/올리브영/쿠팡 검색 결과 페이지가 캡차·봇 차단 없이 RPA로 접근 가능한지
- 쿠팡 이름-매칭의 실제 정확도 (상위 1개 자동 적용이 실무에서 얼마나 틀리는지)
