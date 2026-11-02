from __future__ import annotations

import math

from .settings import Coupon


def apply_coupons(price: int, coupons: list[Coupon]) -> int:
    """Stacked coupons, each applied to the already-discounted price and capped.
    5%(cap 50,000) + 10%(cap 200,000) on 100,000 -> 95,000 -> 85,500.
    Result is floored to 10 KRW."""
    current = float(price)
    for c in coupons:
        current -= min(current * c.rate, c.cap)
    return int(current // 10 * 10)


def coupon_warning(coupons: list[Coupon], conservative: list[Coupon]) -> str | None:
    """Warns when configured coupons are more aggressive than the conservative
    baseline — sheets built on them go stale the moment a coupon expires."""
    if not conservative:
        return None
    total = sum(c.rate for c in coupons)
    base = sum(c.rate for c in conservative)
    if total <= base + 1e-9:
        return None
    fmt = lambda cs: "+".join(f"{round(c.rate * 100)}%" for c in cs)
    return (
        f"보수 기준({fmt(conservative)}) 초과 - 쿠폰({fmt(coupons)}) 유효기간/적용조건을 재확인하세요"
    )


def coupon_label(coupons: list[Coupon]) -> str:
    rates = "+".join(f"{round(c.rate * 100)}%" for c in coupons)
    caps = "/".join(f"{c.cap:,}" for c in coupons)
    return f"{rates} (cap {caps})"


def net_margin(sell_price: int, cost: int, fee_rate: float, shipping: int) -> int:
    return int(sell_price - sell_price * fee_rate - cost - shipping)


def list_price(competitor_price: int, undercut: int) -> int:
    """List just below the cheapest competitor, rounded down to 100 KRW."""
    return int(math.floor((competitor_price - undercut) / 100) * 100)
