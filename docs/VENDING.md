# 2종 자판기 (브랜드 상품 자동 소싱)

| 자판기 | 하는 일 | 결과물 |
|---|---|---|
| 1. Kick Monitor | 브랜드별로 무신사·29cm·오케이몰을 돌며 **신상품 / 가격 하락** 감지 | 디스코드 알림(브랜드·이전가·현재가·쿠폰 적용가·사이즈) |
| 2. 품번 소싱표 | 소싱처 상품과 네이버 직구 스토어 상품을 **품번으로 매칭**하고, 쿠폰 적용 원가와 수수료·배송비를 뺀 마진 계산 | `output/sourcing_YYYYMMDD_HHMM.xlsx` |

검증된 브랜드 정품을 같은 품번으로 파는 구조라 상세페이지를 따로 만들지 않아도 된다.

## 실행

```bash
python run_all.py                      # dry-run: fixtures/vending/*.json으로 동작 확인
python run_all.py --live               # 실제 사이트 (아래 보정 먼저!)
python run_all.py --live --discord --loop 30   # 30분마다 반복 + 디스코드 알림
```

첫 실행은 소싱처마다 **기준선만 저장**한다(기존 상품 수만 개에 알림이 쏟아지지 않도록).
두 번째 실행부터 새 상품번호와 `price_drop_threshold` 이상 떨어진 가격을 알린다.

## 설정 (`data/vending/settings.json`, 예시를 복사해서 사용)

- `brands` / `excluded_brands`: 대상 브랜드와 제외 브랜드 (예: bape)
- `coupons`: 중복 적용 쿠폰. 예: `5%(cap 5만) + 10%(cap 20만)`. 할인율이 `conservative_coupons`보다
  높으면 매 사이클 경고를 띄운다. 쿠폰이 만료되면 소싱표의 마진이 사라지기 때문이다.
- `market_fee_rate`, `shipping_cost`, `min_margin`, `undercut`: 마진 계산 기준
- `cache_ttl_minutes`: 이 시간 안에는 다시 수집하지 않고 캐시 사용 (`data/vending/cache/`)
- `data/vending/blacklist.txt`: 제외할 상품번호 (`123456` 또는 `musinsa:123456`)
- `.env`의 `VENDING_DISCORD_WEBHOOK_URL`: 디스코드 채널 > 연동 > 웹후크 URL

## 사이트 보정 (중요)

`sources`의 URL과 필드 매핑은 **실제 사이트에서 검증하지 않은 추정값**이다. 개발 환경에서는
해당 사이트에 접속할 수 없었다. 무신사 항목은 추정 엔드포인트이고, 29cm·오케이몰·네이버 스토어는
`CALIBRATE_ME`로 비워 두었다. `brand_ids`가 비어 있는 소스는 자동으로 건너뛴다.

보정 방법:
1. 크롬에서 해당 사이트의 브랜드 상품 목록을 열고 F12 > Network > Fetch/XHR를 연다.
2. 상품 목록 JSON을 돌려주는 요청을 찾아 URL을 `url`에 넣는다. 브랜드 자리는 `{brand_id}`,
   페이지 자리는 `{page}`로 바꾼다.
3. 응답에서 상품 배열 위치를 `list_path`(예: `data.list`)에, 각 필드 경로를 `fields`에 적는다.
   점으로 경로를 표기하고 배열 인덱스도 쓸 수 있다(예: `images.0.url`).
4. `brand_ids`에 `"브랜드명": "사이트 브랜드 ID"`를 채운다.

품번(`style_code`)이 목록 API에 없는 사이트도 있다. 그런 사이트는 신상품 알림에는 쓸 수 있지만
소싱표 매칭에서는 빠진다.

## 반드시 지킬 것

- 각 사이트의 이용약관과 robots 정책을 확인하고, `request_delay_sec`를 넉넉하게 둘 것.
  짧은 주기의 대량 수집은 차단되거나 약관 위반이 될 수 있다.
- 병행수입·구매대행으로 팔 때는 해당 브랜드의 판매 제한, 상표권 이슈, 스마트스토어의
  구매대행 정책(해외배송 표기, 통관 등)을 확인할 것. 문제가 된 상품은 블랙리스트에 넣는다.
- 소싱표는 "후보"다. 쿠폰 적용 조건, 실제 재고, 사이즈를 확인한 뒤 등록할 것.
