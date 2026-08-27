# topview-only-shorts

구글 쇼핑 검색 → TopView 입력 정보 준비 스킬.
AI 대본 생성 없이 제품 정보(이름·URL·이미지)를 TopView.ai에 바로 붙여넣을 수 있도록 준비한다.

**필요한 환경변수**: `GOOGLE_API_KEY`, `GOOGLE_CX` (검색용)
**AI 키 불필요**: Gemini·GPT 호출 없음 — TopView 자체 AI를 사용한다.

## 실행 방식

이 스킬이 로드되면 Claude는 아래 단계를 바로 실행한다.
설명하거나 코드를 보여주지 말고, 명령을 실행하고 결과를 출력한다.

---

### 1. 키워드 확인

사용자 메시지에 검색할 상품명/키워드가 있으면 그것을 쓴다.
없으면 한 줄만 물어본다: "어떤 상품으로 TopView 영상을 만들까요?"

### 2. 검색 실행

```bash
python -m shopping_shorts_sync google-shorts search -k "<키워드>" --live
```

결과 목록을 보여주고, 어떤 상품을 쓸지 확인한다.
(결과가 1개거나 명확하면 바로 0번으로 진행)

### 3. TopView 입력 정보 출력 (AI 생성 없음)

```bash
python -m shopping_shorts_sync google-shorts run -k "<키워드>" --live --index <번호> --no-script
```

`--no-script` 플래그가 AI 호출을 건너뛰고 제품 정보만 출력한다.
키 없이도 검색(`--live`)은 안 되므로, 키가 없으면 `--dry-run`으로 실행한다.

### 4. 결과 출력

출력된 TopView 입력 정보(제품명·가격·이미지 URL·제품 URL)를
그대로 사용자에게 보여준다.

### 5. TopView 안내 (한 줄만)

"위 정보를 TopView.ai에 붙여넣으면 AI가 자동으로 영상을 만들어줍니다."
