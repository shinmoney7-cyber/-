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

## 확인이 필요한 열린 질문

- 쿠팡파트너스 API의 정확한 HMAC 서명 포맷(헤더 이름, 날짜 포맷, 서명 대상 문자열에 쿼리
  스트링 포함 여부)은 실제 API 키 발급 후 공식 문서로 재확인 필요
- 쿠팡 딥링크 API 1회 호출당 최대 URL 개수/레이트 리밋
- 인포크 링크 카드 수정 시 카드 순서(정렬)까지 유지해야 하는지, 아니면 필드 교체만으로
  충분한지
- 다이소몰/올리브영/쿠팡 검색 결과 페이지가 캡차·봇 차단 없이 RPA로 접근 가능한지
- 쿠팡 이름-매칭의 실제 정확도 (상위 1개 자동 적용이 실무에서 얼마나 틀리는지)
