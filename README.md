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

모든 테스트는 목(mock) 기반이라 네트워크 접근 없이 통과해야 한다. `test_inpock_rpa.py`는
`fixtures/inpock_fixture_site/`의 가짜 페이지를 사용하는 **구조 테스트**이며, 실제
link.inpock.co.kr 사이트를 검증하지 않는다.
