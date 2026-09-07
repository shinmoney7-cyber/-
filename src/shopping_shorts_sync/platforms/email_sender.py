"""Email sender using Gmail SMTP (or App Password).

For Gmail: use an App Password from https://myaccount.google.com/apppasswords
Or set EMAIL_USE_OAUTH=true to use the Gmail API (requires google-auth).
"""

from __future__ import annotations

import logging
import smtplib
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

log = logging.getLogger(__name__)


@dataclass
class EmailResult:
    success: bool
    recipients_sent: list[str]
    error: Optional[str]


class EmailSender:
    """Sends HTML email newsletters via Gmail SMTP."""

    def __init__(
        self,
        sender: str,
        password: str,
        smtp_host: str = "smtp.gmail.com",
        smtp_port: int = 587,
    ):
        self.sender = sender
        self.password = password
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port

    def send(
        self,
        recipients: list[str],
        subject: str,
        html_body: str,
        plain_body: str = "",
    ) -> EmailResult:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.sender
        msg["To"] = ", ".join(recipients)

        if plain_body:
            msg.attach(MIMEText(plain_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.login(self.sender, self.password)
                server.sendmail(self.sender, recipients, msg.as_string())
            log.info("Email sent to %d recipient(s)", len(recipients))
            return EmailResult(True, recipients, None)
        except Exception as exc:
            log.exception("Email send failed")
            return EmailResult(False, [], str(exc))

    # ------------------------------------------------------------------
    # Template builders
    # ------------------------------------------------------------------

    @staticmethod
    def build_product_newsletter_html(
        products: list[dict],
        intro: str = "오늘의 추천 상품",
    ) -> str:
        items_html = ""
        for p in products:
            items_html += f"""
<tr>
  <td style="padding:16px;border-bottom:1px solid #eee;">
    <a href="{p.get('deeplink', p.get('coupang_url', '#'))}" target="_blank">
      <img src="{p.get('thumbnail', '')}" width="120" style="border-radius:4px;" alt="{p.get('name', '')}">
    </a>
  </td>
  <td style="padding:16px;border-bottom:1px solid #eee;vertical-align:top;">
    <strong>{p.get('name', '')}</strong><br>
    <span style="color:#888;font-size:12px;">{p.get('category', '')}</span><br><br>
    <a href="{p.get('deeplink', p.get('coupang_url', '#'))}"
       style="background:#e81f25;color:#fff;padding:8px 16px;border-radius:4px;text-decoration:none;font-size:13px;">
      쿠팡에서 보기
    </a>
  </td>
</tr>"""

        return f"""
<!DOCTYPE html>
<html lang="ko">
<head><meta charset="utf-8"><title>쇼핑 추천</title></head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:sans-serif;">
  <table width="600" align="center" style="background:#fff;margin:24px auto;border-radius:8px;overflow:hidden;">
    <tr>
      <td style="background:#e81f25;padding:24px;text-align:center;">
        <h1 style="margin:0;color:#fff;font-size:22px;">{intro}</h1>
      </td>
    </tr>
    <tr><td><table width="100%">{items_html}</table></td></tr>
    <tr>
      <td style="padding:16px;text-align:center;font-size:11px;color:#aaa;">
        이 메일은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.<br>
        수신거부는 회신해 주세요.
      </td>
    </tr>
  </table>
</body>
</html>""".strip()


class MockEmailSender(EmailSender):
    def __init__(self):
        self.sender = "mock@gmail.com"
        self.password = "mock"
        self.smtp_host = "smtp.gmail.com"
        self.smtp_port = 587

    def send(self, recipients, subject, html_body, plain_body=""):
        log.info("[MOCK] Email: '%s' -> %s", subject, recipients)
        return EmailResult(True, recipients, None)
