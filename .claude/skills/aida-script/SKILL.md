---
name: aida-script
description: 상품별 AIDA(주의-흥미-욕망-행동) 대본 후보 5개를 작성해 data/scripts/<product_id>.json에 저장하고, 필요하면 script select로 연동한다
---

# AIDA 대본 작성

## 목표
상품 하나당 AIDA 구조의 대본 후보를 **정확히 5개** 만들어 `data/scripts/<product_id>.json`에 저장한다. 이 도구는 대본을 자동 생성하지 않으므로, 이 스킬로 직접 작성한다.

## 입력 확인
1. `data/products.example.json` 또는 사용자가 지정한 입력 파일에서 `product_id`, `name`, `category`를 읽는다.
2. 기존 파일 `data/scripts/<product_id>.json`이 있으면 먼저 읽고, 덮어쓰기 전에 사용자에게 확인한다.

## 파일 형식
```json
{
  "product_id": "<product_id>",
  "candidates": [
    {"id": 1, "attention": "...", "interest": "...", "desire": "...", "action": "..."}
  ],
  "selected_id": null
}
```
- `candidates`는 `id` 1~5, 정확히 5개.
- 각 필드는 한국어 한두 문장의 쇼츠 대사로 쓴다.
- `selected_id`는 사용자가 고르기 전까지 `null`로 둔다.

## 작성 규칙
- 5개가 서로 다른 훅(문제 공감, 가격 놀람, 시간 절약, 특정 상황, 체험 후기 등)을 쓴다. 같은 문장 구조를 반복하지 않는다.
- 과장 광고나 검증되지 않은 효능(의학적 효과, "1위", 근거 없는 수치)을 쓰지 않는다.
- `action`에는 쇼핑태그나 구독 같은 행동 유도만 넣는다.

## 연동
사용자가 하나를 고르면 다음을 실행한다. 이 명령은 `data/state.json`에 반영되므로 사용자 확인 후에만 실행한다.
```bash
python -m shopping_shorts_sync script select --product-id <product_id> --candidate-id <n> --input <input_file>
python -m shopping_shorts_sync script show --product-id <product_id>
```

## 완료 보고
- 저장한 파일 경로, 후보 5개의 `attention` 요약, 연동 여부를 알려준다.
