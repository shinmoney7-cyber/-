# shopping-shorts-sync — Claude 작업 규칙

쿠팡 딥링크 생성 + 인포크 링크 카드 동기화 + 상품 검색/쿠팡 매칭 CLI. 자세한 사용법은 `README.md`, 셀렉터 보정 절차는 `docs/CALIBRATION.md`를 따른다.

## 명령

- 테스트: `pytest` (네트워크 없이 통과해야 함, 현재 56개)
- 드라이런 예: `python -m shopping_shorts_sync sync all --input data/products.example.json --dry-run`
- 기본값은 항상 드라이런. `--live`/`--headed`는 사용자가 명시적으로 요청할 때만 쓴다.

## 절대 규칙

- `playwright install`을 실행하지 않는다. 브라우저는 `.env`의 `PLAYWRIGHT_CHROMIUM_PATH`(이미 설치된 Chromium)를 사용한다.
- `.env`는 직접 수정하지 않는다. 자격증명(쿠팡 키, 인포크 비밀번호, 네이버 시크릿)은 사용자가 직접 넣는다.
- `data/state.json`은 직접 편집하지 않는다. 상태 변경은 CLI(`state reset` 등)로 한다.
- `--live` 실행은 `docs/CALIBRATION.md` 절차(`--headed --dry-run` 확인 → 그다음 `--live`)를 거친 뒤에만 한다.
- `TODO CALIBRATE` 표시가 있는 셀렉터는 실제 사이트에서 확인되기 전까지 검증된 값으로 취급하지 않는다.
- 로그, `debug/` 스크린샷, 커밋 어디에도 비밀번호·쿠키·API 키를 남기지 않는다.

## 대본 작업

- 상품당 AIDA 대본 후보는 정확히 5개, `data/scripts/<product_id>.json`에 저장한다.
- 대본 작성/선택은 `aida-script` 스킬을 사용한다.

## 코드 변경

- 변경 후 `pytest`가 통과하는지 확인한다.
- 커밋과 푸시는 사용자가 요청할 때만 한다.
