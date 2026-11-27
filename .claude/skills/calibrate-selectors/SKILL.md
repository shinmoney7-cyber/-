---
name: calibrate-selectors
description: docs/CALIBRATION.md 절차에 따라 인포크, 다이소, 올리브영, 쿠팡 셀렉터를 실제 사이트에서 보정한다
disable-model-invocation: true
---

# 셀렉터 보정

이 스킬은 실제 계정으로 로그인하고 사이트를 조작하므로 **사용자가 직접 호출할 때만** 실행한다. 비밀번호는 Claude가 입력하지 않는다. 필요하면 사용자가 브라우저에서 직접 로그인한다.

## 사전 확인
1. `docs/CALIBRATION.md`를 읽고 현재 단계를 확인한다.
2. `.env`의 `PLAYWRIGHT_CHROMIUM_PATH`가 존재하는지 확인한다. 값은 출력하지 않는다.
3. `pytest`를 실행해 기준선을 기록한다.

## 인포크 (`src/shopping_shorts_sync/inpock/selectors.py`)
1. 로그인 URL과 로그인 폼 셀렉터를 확인한다. `LoginSelectors`의 `TODO CALIBRATE` 값을 실제 값으로 바꾼다.
2. 로그인 후 harujin/shinjh 페이지 전환 방식을 확인하고 `PAGE_SWITCH_URL_TEMPLATE`을 갱신한다.
3. 편집기에서 링크 추가, 제목/URL/썸네일 입력, 저장 버튼의 셀렉터를 확인하고 `EditorSelectors`를 갱신한다.
4. 카드를 특정하는 방법이 안정적인지 확인한다. `data-testid` 같은 속성을 우선한다.

## 검색/매칭 (`src/shopping_shorts_sync/search/selectors.py`)
1. 다이소, 올리브영, 쿠팡의 검색 URL 패턴을 확인하고 `SEARCH_URL_TEMPLATE`을 갱신한다.
2. 검색 결과 카드 구조(이름, 이미지, 링크, 가격)의 셀렉터를 확인한다.
3. 로그인 없이 결과가 보이는지 확인한다.

## 각 단계 후 검증
- 셀렉터를 바꿀 때마다 `pytest tests/test_inpock_rpa.py tests/test_search_rpa.py`를 실행한다.
- 구조가 바뀌었으면 `fixtures/` 아래 가짜 페이지도 실제 구조에 맞게 함께 갱신한다.

## 실행 순서 (반드시 지킨다)
1. `--headed --dry-run`으로 실행해 브라우저에서 단계별 동작을 확인한다.
2. 실패하면 `debug/` 스크린샷을 확인한다. 스크린샷에 자격증명이 보이면 사용자에게 알린다.
3. 문제가 없음을 사용자가 확인한 뒤에만 `--live`를 실행한다.

## 금지
- 사용자 확인 없이 `--live`를 실행하지 않는다.
- 로그인 정보를 파일이나 출력에 남기지 않는다.
