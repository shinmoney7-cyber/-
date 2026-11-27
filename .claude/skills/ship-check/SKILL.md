---
name: ship-check
description: 커밋 전 점검. pytest 실행, 비밀값과 상태 파일이 스테이징되지 않았는지 확인, 변경 요약과 커밋 메시지 초안을 만든다
disable-model-invocation: true
---

# 커밋 전 점검

이 스킬은 커밋과 푸시 전에 사용자가 직접 호출합니다. 커밋과 푸시 자체는 사용자가 확인하기 전에는 하지 않습니다.

## 1. 테스트
```bash
python -m pytest -q
```
실패하면 중단하고 실패 내용을 보고합니다. 테스트를 건너뛰거나 삭제해서 통과시키지 않습니다.

## 2. 금지 경로 확인
```bash
git status --short
git diff --cached --name-only
```
다음 항목이 스테이징되었거나 추적 대상에 들어 있으면 중단하고 사용자에게 알립니다.
- `.env` (단, `.env.example`은 허용)
- `data/state.json`
- `debug/` 아래 파일
- 스크린샷, 쿠키, 토큰이 든 파일

## 3. 비밀값 스캔
변경된 파일에서 다음 패턴을 찾습니다.
```bash
git diff --cached | grep -nE "(PASSWORD|SECRET|ACCESS_KEY|api[_-]?key|Bearer )\s*[=:]\s*['\"]?[A-Za-z0-9]" || echo "no obvious secrets"
```
일치하는 줄이 있으면 값은 출력하지 않고 파일 경로와 줄 번호만 보고합니다.

## 4. 변경 요약
- 바뀐 파일 목록과 각 파일의 변경 목적을 한 줄씩 정리합니다.
- `src/shopping_shorts_sync/inpock/selectors.py` 또는 `search/selectors.py`가 바뀌었다면 `TODO CALIBRATE`가 남아 있는지도 적습니다.

## 5. 커밋 메시지 초안
- 제목은 한 줄, 변경 목적 중심으로 씁니다.
- 본문은 변경 요약을 불릿으로 씁니다.
- 사용자 확인 없이 `git commit`을 실행하지 않습니다.

## 6. 결과
통과 여부, 발견한 문제, 커밋 메시지 초안을 보고합니다. 커밋과 푸시는 사용자가 "진행"이라고 말한 뒤에만 합니다.
