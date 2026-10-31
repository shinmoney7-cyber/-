/**
 * 사주마루 Google Form → Gmail 자동 주문 이메일 변환
 *
 * 설치 방법:
 * 1. Google Form 열기 → 점 3개 메뉴 → Apps Script
 * 2. 이 코드 전체 붙여넣기
 * 3. 저장 후 "트리거 추가" → onFormSubmit → 폼 제출시 실행
 * 4. 권한 허용
 *
 * ── 유입 채널 추적 방법 ──────────────────────────────────────
 * "어디서 보고 오셨나요?" 질문을 폼에서 삭제하세요.
 * 대신 채널별로 다른 단축 링크를 사용합니다:
 *
 *   Google Form → 응답 → 🔗 링크 아이콘 클릭 → "링크 복사"
 *   이 기본 URL 뒤에 ?usp=sf_link 대신 아래처럼 채널 코드를 붙임:
 *
 *   인스타 사주마루77  → 폼URL + &entry.CHANNEL=사주마루77인스타
 *   인스타 사주보는언니 → 폼URL + &entry.CHANNEL=사주보는언니인스타
 *   스레드            → 폼URL + &entry.CHANNEL=스레드
 *   카카오톡          → 폼URL + &entry.CHANNEL=카카오톡
 *   네이버 블로그      → 폼URL + &entry.CHANNEL=네이버블로그
 *
 * ※ entry.CHANNEL 대신 실제 필드 entry ID를 넣어야 합니다.
 *    폼 편집화면 → 미리보기(눈 아이콘) → 해당 필드 우클릭 → 검사
 *    → entry.XXXXXXXXX 번호 확인
 * ────────────────────────────────────────────────────────────
 */

var OPERATOR_EMAIL = "sajumaru7@gmail.com";

// Form 필드 이름 (실제 Form 질문과 정확히 일치해야 함)
var FIELD = {
  name:          "이름",
  birth:         "생년월일",
  birth_type:    "양력/음력",
  hour:          "태어난 시간",
  gender:        "성별",
  product:       "신청 항목",
  delivery:      "결과 받을 곳",
  delivery_type: "결과 받는 방법",
  request:       "요청사항 (선택)",
  channel:       "채널코드",        // ← 폼에 숨겨진 필드 (고객이 직접 입력 X, URL로 자동입력)
};

// 시간 텍스트 → 시주명 변환
function parseHour(hourText) {
  if (!hourText || hourText.includes("모름") || hourText.includes("몰라")) return "모름";
  var m = hourText.match(/(\d{1,2})시/);
  if (!m) return hourText;
  var h = parseInt(m[1]);
  if (hourText.includes("오후") && h < 12) h += 12;
  if (hourText.includes("오전") && h === 12) h = 0;
  var siNames = ["자시","자시","축시","축시","인시","인시","묘시","묘시",
                 "진시","진시","사시","사시","오시","오시","미시","미시",
                 "신시","신시","유시","유시","술시","술시","해시","해시"];
  return siNames[h] || hourText;
}

function onFormSubmit(e) {
  try {
    var resp  = e.response;
    var items = resp.getItemResponses();
    var data  = {};

    items.forEach(function(item) {
      data[item.getItem().getTitle()] = item.getResponse();
    });

    var name          = data[FIELD.name] || "";
    var birth         = data[FIELD.birth] || "";
    var birthType     = data[FIELD.birth_type] || "양력";
    var hourRaw       = data[FIELD.hour] || "모름";
    var gender        = data[FIELD.gender] || "여성";
    var product       = data[FIELD.product] || "";
    var delivery      = data[FIELD.delivery] || "";
    var deliveryType  = data[FIELD.delivery_type] || "이메일";
    var request       = data[FIELD.request] || "";
    var channel       = data[FIELD.channel] || "경로미상";  // URL로 자동 입력된 채널

    if (!name || !birth) return;

    var hourSi = parseHour(hourRaw);
    var birthLabel = birthType === "음력" ? birth + " (음력)" : birth;

    // 상품이 배열(체크박스 복수선택)이면 줄 구분
    var productLines = Array.isArray(product)
      ? product.map(function(p){ return "ㆍ" + p; }).join("\n")
      : "ㆍ" + product;

    // check_orders.py 파싱 형식
    var body = [
      "성함: " + name,
      "생년월일: " + birthLabel,
      "성별: " + gender,
      "태어난 시간: " + hourSi,
      "전달 방법: " + deliveryType,
      "전달 받을 곳: " + (delivery || OPERATOR_EMAIL),
      "",
      "신청 항목:",
      productLines,
      "",
      "요청사항: " + (request || "없음"),
      "",
      "--- 구글폼 자동 주문 · 유입채널: " + channel + " ---",
    ].join("\n");

    var subject = "[사주마루] 폼 신청 - " + name + " " + birth;

    GmailApp.sendEmail(OPERATOR_EMAIL, subject, body, {
      name: "사주마루 주문봇",
    });

    console.log("✅ 주문 메일 발송: " + name + " / 채널: " + channel);

  } catch (err) {
    console.error("❌ 오류: " + err);
    GmailApp.sendEmail(OPERATOR_EMAIL,
      "[사주마루] 폼 신청 오류",
      "오류 내용: " + err.toString() + "\n\n응답 데이터: " + JSON.stringify(e));
  }
}
