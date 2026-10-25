---
name: coupang-partners-autolink
description: 쿠팡 상품 URL(또는 상품 목록)을 쿠팡파트너스 오픈API로 자동 변환해 제휴 딥링크를 생성하고, 인포크(링크트리형 상품 허브) 페이지에 자동 반영하는 워크플로우. 트리거 - "쿠팡파트너스 자동연동", "딥링크 자동생성", "인포크 링크 업데이트", 쿠팡 URL + 파트너스/딥링크 조합.
model: sonnet
---

# 쿠팡파트너스 자동 딥링크 + 인포크 연동 스킬

> 사람이 쿠팡파트너스 사이트에 로그인해서 링크를 하나씩 수동 변환하던 작업을,
> 오픈API 호출 한 번으로 대체하고 결과를 인포크 페이지에 자동 반영하는 것이 이 스킬의 목적이다.
> 모든 대화와 로그 메시지는 한국어로 작성한다.

## 설치

이 스킬은 이 저장소(`shopping-shorts-sync`)의 CLI로 실행한다. 저장소 루트에서:

```bash
pip install -r requirements.txt   # requests, python-dotenv, click, playwright
cp .env.example .env              # 키·계정 값 채우기
```

Playwright는 `playwright install`을 하지 않고 `.env`의 `PLAYWRIGHT_CHROMIUM_PATH`(이미 설치된 Chromium)를 쓴다.

## 입력

- 쿠팡 상품/검색 URL 1개 이상 (필수). 최대 100개/요청 (쿠팡 API 제한).
- `COUPANG_ACCESS_KEY`, `COUPANG_SECRET_KEY` — 쿠팡파트너스 대시보드 > 오픈API 발급 메뉴에서 발급받은 키 (필수, 사용자가 직접 발급). 키가 없으면 `COUPANG_API_MODE=mock`으로 전체 흐름을 미리 돌려볼 수 있다.
- 인포크 계정(`INPOCK_EMAIL`, `INPOCK_PASSWORD`)과 대상 페이지(`harujin` / `shinjh`).

## 진행 체크리스트

순서대로 진행하고, 각 단계가 끝나면 체크한다.

- [ ] 1. 키 확인 — `.env`에 키 2개가 있는지 (없으면 mock 모드로 진행)
- [ ] 2. URL 목록 확인받기 — 상품 목록 JSON으로 정리
- [ ] 3. 딥링크 생성 — 실패 항목은 표로 따로 보고
- [ ] 4. 인포크 반영 — dry-run 결과 보여주기 → 승인 → 실제 반영
- [ ] 5. 샘플 클릭 확인 — 실패하면 3단계로 돌아간다

## 사전 확인

1. **API 키 보유 여부**를 먼저 묻는다. 없으면 발급 절차부터 안내한다:
   - 쿠팡파트너스(partners.coupang.com) 로그인 → 마이페이지 → "오픈API 이용" 메뉴에서 액세스키/시크릿키 발급.
   - 심사 후 발급되는 경우가 있어 즉시 안 될 수 있음을 미리 알린다.
2. **키를 대화창에 붙여넣지 말라고 안내한다.** `.env`에만 저장하고 코드에서는 환경변수로만 읽는다. 사용자가 실수로 키를 채팅에 붙여넣으면, 그 값을 코드/로그/커밋에 남기지 말고 즉시 `.env`로 옮기도록 안내한다.
3. 인포크 셀렉터 보정 여부를 확인한다. 실제 계정으로 처음 실행하기 전에는 `docs/CALIBRATION.md` 절차를 먼저 거쳐야 한다.

## 워크플로우 (4단계)

### Phase 1. 원본 URL 수집

- 사용자로부터 변환할 쿠팡 URL 목록을 받는다 (상품 상세페이지, 검색결과, 골드박스 등 모두 가능).
- `data/products.example.json` 형식(`id`, `name`, `coupang_url`, `thumbnail`, `category`, `target_page`, `enabled`)으로 정리해 확인받는다.

### Phase 2. 딥링크 생성 (쿠팡파트너스 오픈API 호출)

정해진 명령으로만 실행한다:

```bash
python -m shopping_shorts_sync deeplink generate --input <상품목록.json>
```

- 엔드포인트·HMAC 서명 구현: `src/shopping_shorts_sync/coupang/client.py`, `src/shopping_shorts_sync/coupang/signing.py`
- 결과는 `data/state.json`에 상품별로 기록된다 (`python -m shopping_shorts_sync state show`로 확인).
- 상품별로 변환 실패(`rCode` != "0")가 섞여 나올 수 있으므로, 성공/실패를 분리해서 사용자에게 표로 보고한다.

### Phase 3. 인포크 링크 자동 반영 ⛔ dry-run → 승인 게이트

인포크에는 공개 API가 없어 Playwright 브라우저 자동화로 링크 카드를 등록/수정한다. 실제 페이지를 덮어쓰는 단계이므로 아래 순서를 바꾸지 않는다.

1. dry-run으로 바뀔 내용을 확인한다:
   ```bash
   python -m shopping_shorts_sync inpock sync --input <상품목록.json> --dry-run
   ```
2. dry-run 결과(추가/수정될 카드 목록)를 표로 보여주고 **멈춰서 승인을 기다린다.**
3. 승인 후에만 `--dry-run`을 빼고 같은 명령을 실행한다.

이 저장소가 아닌 다른 링크 페이지(정적 JSON, 다른 노코드 툴 등)를 쓰는 경우에는 구조(파일 스키마나 API)를 먼저 공유받고, 모르는 상태로 파일 포맷을 가정해 코드를 만들지 않는다.

반영 후 실제 페이지에서 링크 1개 이상을 샘플 클릭해, 쿠팡 상품 페이지로 정상 연결되는지 확인하도록 안내한다.

### Phase 4. 정기 갱신 자동화 (선택)

상품이 계속 추가/교체되는 구조라면:
- cron/스케줄러로 `python -m shopping_shorts_sync sync all --input <상품목록.json>`을 주기 실행하는 구조를 제안한다. 같은 입력을 다시 돌려도 바뀐 상품만 처리된다.
- 실제 스케줄 실행 환경(로컬 PC 상시 켜둠 / 서버 / GitHub Actions 등)은 사용자 환경에 맞게 함께 정하고, 이 컨테이너 안에서는 스케줄러가 지속 실행되지 않는다는 점을 알린다.

## 검사 → 고치기 → 반복

- 검사 기준: Phase 2 성공/실패 표에서 실패 0건, Phase 3 샘플 클릭이 쿠팡 상품 페이지로 연결됨.
- 실패가 있으면 원인을 고치고(URL 재확인, 시스템 시간, 셀렉터 보정) 해당 단계를 다시 실행한다. 모두 통과해야 끝이다.
- 이 기준에 없는 이유로 걸렸다면, 작업 끝에 새 규칙 1개를 제안하고 사용자 승인을 받는다.

## 오류 처리 (실전 유의사항)

- **API 요청 제한**: 대량 URL은 배치로 나눠 호출한다 (`.env`의 `COUPANG_BATCH_SIZE`).
- **rCode 오류**: `400204` 등은 딥링크 변환 불가 상품(품절/판매중지 등)일 수 있다. 실패 목록을 사용자에게 별도로 보고하고 원본 URL을 재확인하게 한다.
- **시크릿 키 노출 금지**: 코드/커밋/로그 어디에도 `SECRET_KEY` 평문을 남기지 않는다. `.env`는 `.gitignore` 대상이다.
- **시간 동기화**: HMAC 서명에 GMT 기준 타임스탬프가 들어가므로, 시스템 시간이 어긋나면 인증이 실패한다. 인증 실패 시 가장 먼저 시스템 시간을 의심한다.

## 대화 톤

- 정중한 한국어, 간결하게.
- API 키·시크릿 관련 안내는 항상 보안 주의사항을 먼저 짚고 넘어간다.
