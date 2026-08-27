# google-flow-shorts

구글 쇼핑 검색 → Gemini 대본/자막/해시태그 → TopView 패키지 생성 스킬.

**필요한 환경변수**: `GOOGLE_API_KEY`, `GOOGLE_CX`

## 실행 방식

이 스킬이 로드되면 Claude는 아래 단계를 바로 실행한다.
설명하거나 코드를 보여주지 말고, 명령을 실행하고 결과를 출력한다.

---

### 1. 키워드 확인

사용자 메시지에 검색할 상품명/키워드가 있으면 그것을 쓴다.
없으면 한 줄만 물어본다: "어떤 상품으로 만들까요?"

### 2. 검색 실행

```bash
python -m shopping_shorts_sync google-shorts search -k "<키워드>" --live
```

결과 목록을 보여주고, 어떤 상품을 쓸지 확인한다.
(결과가 1개거나 명확하면 바로 0번으로 진행)

### 3. 패키지 생성 실행 (Gemini 엔진)

```bash
python -m shopping_shorts_sync google-shorts run -k "<키워드>" --live --index <번호> --engine gemini
```

`--live`가 동작하려면 `.env`에 `GOOGLE_API_KEY`와 `GOOGLE_CX`가 있어야 한다.
없으면 `--dry-run`(기본값)으로 실행해 모의 결과를 보여주고,
"실제 결과를 원하면 `.env`에 키를 추가하세요" 라고 안내한다.

### 4. 결과 출력

CLI 출력을 그대로 보여준다. 추가 설명 없이 결과만 깔끔하게 제시한다.
Gemini가 생성한 대본, 자막, 배경음악 제안, 해시태그 10개+가 포함된다.

### 5. 후속 제안 (한 줄만)

"다른 상품도 만들까요?" 또는 "GPT 버전으로도 만들어볼까요?"
