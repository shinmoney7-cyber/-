from __future__ import annotations

import logging
from datetime import datetime

import requests

from .detect import Event

log = logging.getLogger(__name__)


def format_event(ev: Event) -> dict:
    it = ev.item
    titles = {"new": "🆕 신상품", "price_drop": f"📉 가격 하락 {ev.drop_rate:.0%}",
              "unlist": "🚨 판매 중지 필요", "check": "⚠️ 소싱처 확인 필요"}
    title = titles.get(ev.kind, ev.kind) + f" | {it.name}"
    fields = [{"name": "브랜드", "value": it.brand or "-", "inline": True}]
    if ev.reason:
        fields.insert(0, {"name": "사유", "value": ev.reason, "inline": False})
    if ev.prev_price:
        fields.append({"name": "이전 가격", "value": f"{ev.prev_price:,} KRW", "inline": True})
    if it.price:
        fields.append({"name": "가격", "value": f"{it.price:,} KRW", "inline": True})
    if ev.our_cost is not None:
        fields.append({"name": "쿠폰 적용가", "value": f"{ev.our_cost:,} KRW", "inline": True})
    if it.sizes:
        fields.append({"name": "사이즈", "value": it.sizes, "inline": False})
    fields.append({"name": "소싱처", "value": it.source, "inline": True})
    embed = {"title": title[:250], "url": it.url or None, "fields": fields,
             "footer": {"text": f"Kick Monitor · {datetime.now():%Y-%m-%d %H:%M}"}}
    if it.image:
        embed["thumbnail"] = {"url": it.image}
    return embed


class ConsoleNotifier:
    def __init__(self, echo=print):
        self.echo = echo
        self.sent: list[Event] = []

    def send(self, events: list[Event]) -> None:
        for ev in events:
            self.sent.append(ev)
            e = format_event(ev)
            body = " / ".join(f"{f['name']}: {f['value']}" for f in e["fields"])
            self.echo(f"  [알림] {e['title']}\n         {body}")


class DiscordNotifier:
    """Discord incoming webhook (Server settings > Integrations > Webhooks).
    Discord allows up to 10 embeds per message."""

    def __init__(self, webhook_url: str, timeout: float = 10.0):
        if not webhook_url:
            raise ValueError("VENDING_DISCORD_WEBHOOK_URL is required for Discord alerts")
        self.webhook_url = webhook_url
        self.timeout = timeout

    def send(self, events: list[Event]) -> None:
        for i in range(0, len(events), 10):
            chunk = [format_event(ev) for ev in events[i:i + 10]]
            resp = requests.post(self.webhook_url, json={"username": "Kick Monitor", "embeds": chunk},
                                 timeout=self.timeout)
            resp.raise_for_status()
