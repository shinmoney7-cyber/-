/**
 * 사주마루 Google Form → Gmail 자동 주문 이메일 변환
 *
 * 설치 방법:
 * 1. Google Form 열기 → 점 3개 메뉴 → Apps Script
 * 2. 이 코드 붙여넣기
 * 3. OPERATOR_EMAIL 확인 (shinmoney7@gmail.com)
 * 4. 저장 후 "트리거 추가" → onFormSubmit → 폼 제출시 실행
 * 5. 권한 허용
 */

var OPERATOR_EMAIL = "shinmoney7@gmail.com";

// Form 필드 이름 (실제 Form 질문과 정확히 일치해야 함)
var FIELD = {
  name:          "이름",
  birth:         "생년월일",       // 예: 1990.05.20
  birth_type:    "양력/음력",      // "양력" or "음력"
  hour:          "태어난 시간",    // 예: "오전 6시 30분" or "모름"
  gender:        "성별",           // "여성" or "남성"
  product:       "신청 항목",      // 체크박스 또는 드롭다운
  customer_email:"이메일",         // 결과 받을 이메일
  from_where:    "어디서 보고 오셨나요",
  request:       "요청사항",
};

// 시간 텍스트 → 시시 (24h) 변환
function parseHour(hourText) {
  if (!hourText || hourText.includes("모름") || hourText.includes("몰라")) return "모름";
  var m = hourText.match(/(\d{1,2})시/);
  if (!m) return hourText;
  var h = parseInt(m[1]);
  if (hourText.includes("오후") && h < 12) h += 12;
  if (hourText.includes("오전") && h === 12) h = 0;
  // 시주명으로 변환
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

    var name         = data[FIELD.name] || "";
    var birth        = data[FIELD.birth] || "";
    var birthType    = data[FIELD.birth_type] || "양력";
    var hourRaw      = data[FIELD.hour] || "모름";
    var gender       = data[FIELD.gender] || "여성";
    var product      = data[FIELD.product] || "평생운";
    var custEmail    = data[FIELD.customer_email] || "";
    var fromWhere    = data[FIELD.from_where] || "";
    var request      = data[FIELD.request] || "";

    if (!name || !birth) return; // 필수 항목 없으면 스킵

    var hourSi = parseHour(hourRaw);
    var birthLabel = birthType === "음력" ? birth + " (음력)" : birth;

    // check_orders.py 가 파싱하는 형식으로 이메일 본문 작성
    var body = [
      "성함: " + name,
      "생년월일: " + birthLabel,
      "성별: " + gender,
      "태어난 시간: " + hourSi,
      "전달 방법: 이메일",
      "전달 받을 곳: " + (custEmail || OPERATOR_EMAIL),
      "",
      "신청 항목:",
      "ㆍ" + (Array.isArray(product) ? product.join("\nㆍ") : product),
      "",
      "유입 경로: " + fromWhere,
      "요청사항: " + request,
      "",
      "--- 구글폼 자동 주문 ---",
    ].join("\n");

    var subject = "[사주마루] 폼 신청 - " + name + " " + birth;

    GmailApp.sendEmail(OPERATOR_EMAIL, subject, body);
    console.log("✅ 주문 메일 발송: " + name);

  } catch (err) {
    console.error("❌ 오류: " + err);
    GmailApp.sendEmail(OPERATOR_EMAIL,
      "[사주마루] 폼 신청 오류",
      "오류 내용: " + err.toString() + "\n\n응답 데이터: " + JSON.stringify(e));
  }
}
