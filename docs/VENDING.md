# 2종 자판기 (브랜드 상품 자동 소싱)

| 자판기 | 하는 일 | 결과물 |
|---|---|---|
| 1. Kick Monitor | 브랜드별로 무신사·29cm·오케이몰을 돌며 **신상품 / 가격 하락** 감지 | 디스코드 알림(브랜드·이전가·현재가·쿠폰 적용가·사이즈) |
| 2. 품번 소싱표 | **소싱처**(네이버직구 스토어 + 오케이몰)에서 쿠폰 적용가로 사서 **판매 기준**(무신사·29cm) 가격 바로 아래로 팔 때 마진이 나는 품번을 찾음 | `output/sourcing_YYYYMMDD_HHMM.xlsx` |

소스마다 `role`(`sourcing` = 사는 곳, `market` = 판매가 기준)과 `detect`(신상품 감지 여부)를 지정한다.
품번은 공백·하이픈을 무시하고 비교하며, 한쪽에 색상/사이즈 코드가 붙은 경우(`591970VCQR1` ↔
`591970VCQR11000`)도 앞부분 6자 이상이 같으면 매칭한다.

### 네이버직구 스토어 (= 소싱처 리스트)

`type: "naver_shop"` 소스는 네이버 쇼핑 공식 검색 API(`.env`의 `NAVER_CLIENT_ID/SECRET`)로
브랜드를 검색한 뒤 **`stores` 목록에 있는 판매처(mallName)만** 남긴다. 품번은 상품명에서 자동
추출한다. 새 소싱처(비밀소싱처 포함)를 찾으면 `stores`에 스토어 이름만 추가하면 된다.
예시의 스토어 이름은 영상 캡처에서 읽은 것이라 철자를 확인할 것.

검증된 브랜드 정품을 같은 품번으로 파는 구조라 상세페이지를 따로 만들지 않아도 된다.

## 오프라인 아울렛 매입 판단

매장에서 본 상품을 `data/vending/outlet_finds.csv`(엑셀에서 CSV로 저장해도 됨)에 적는다.
컬럼은 `날짜,매장,브랜드,품번,상품명,가격,사이즈,수량`이다. 품번은 가격표나 택에 적힌 모델번호를 쓴다.

```bash
python -m shopping_shorts_sync vending outlet --live
```

품목마다 네이버 쇼핑에서 같은 품번을 파는 온라인 판매처를 찾는다. 온라인 최저가보다 100원 낮게
팔았을 때의 마진을 계산하고 결과를 셋으로 나눈다.

- **매입**: 마진이 기준 이상이고 판매처가 2곳 이상
- **보류**: 판매처가 적어서 시세를 믿기 어렵거나, 온라인 판매처가 아예 없음
- **비추천**: 마진이 부족함

결과는 `output/outlet_*.xlsx`(색상 표시)로 저장된다. 아울렛 목록은 `data/vending/outlets.example.json`에 있다.
아울렛 매입은 쿠폰을 적용하지 않고 계산한다. 결제 할인이 있으면 가격 칸에 실제로 낸 금액을 적는다.
네이버 API 키만 있으면 쓸 수 있고, 무신사·29cm 보정은 필요 없다.

## 소싱처 발굴

무신사·29cm에서 파는 품번마다 네이버 쇼핑에서 `브랜드 품번`을 검색한다. 상품명에 그 품번이
실제로 들어 있는 판매처만 남긴 뒤, **시세보다 싸게 파는 품번 수와 쿠폰 적용 후 마진**으로
판매처 순위를 매긴다. 무신사·29cm 같은 판매 플랫폼 자체와 가격비교 묶음("네이버")은 순위에서 뺀다.

```bash
python -m shopping_shorts_sync vending discover            # dry-run (fixtures)
python -m shopping_shorts_sync vending discover --live --apply --min-profitable 2
```

결과는 `output/discover_*.xlsx`에 저장된다. 시트는 "소싱처 순위"(★신규 후보는 노란색 표시)와
"품번별 최저가" 두 개다. `--apply`를 주면 수익 품번이 기준 개수 이상인 신규 판매처를
`data/vending/settings.json`의 `stores`에 자동으로 추가한다. 네이버 검색 API는 하루 25,000회까지
호출할 수 있으니 품번이 많으면 `--limit`으로 나눠서 돌릴 것.

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
