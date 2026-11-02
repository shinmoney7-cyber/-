"""run_all: one automation cycle of the 2종 자판기, logged in STEP format.

STEP 0  신규 감지   — sources with detect=true (무신사/29cm/오케이몰): new products + price drops -> alerts
STEP 1  데이터 로드 — every source per brand (cached with TTL)
STEP 2  소싱 스캔   — 네이버직구 스토어 + 오케이몰 vs 무신사/29cm by 품번 -> xlsx 소싱표
STEP 3  판매 감시   — data/vending/listings.csv 위탁 상품: 소싱처 품절 / 마진 소멸 -> 알림
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .db import SeenDB
from .detect import Event, detect, is_blocked
from .models import Item
from .pricing import apply_coupons, coupon_label, coupon_warning
from .settings import VendingSettings
from .sheet import Opportunity, build_opportunities, write_xlsx


@dataclass
class CycleResult:
    events: list[Event] = field(default_factory=list)
    listing_events: list[Event] = field(default_factory=list)
    opportunities: list[Opportunity] = field(default_factory=list)
    sheet_path: Path | None = None


def run_cycle(settings: VendingSettings, sources, db: SeenDB, blacklist: set[str], notifier,
              out_dir: str | Path, echo=print, listings=None) -> CycleResult:
    res = CycleResult()
    line = "=" * 60
    warn = coupon_warning(settings.coupons, settings.conservative_coupons)
    echo(f"[쿠폰률] {coupon_label(settings.coupons)}" + (f"  ⚠ {warn}" if warn else ""))
    echo(line)
    echo(f"  자동화 사이클 시작: {datetime.now():%Y-%m-%d %H:%M}")
    echo(f"  블랙리스트: {len(blacklist)}개 상품번호 로드")
    echo(line)

    excluded = {x.replace(" ", "") for x in settings.excluded_brands}
    brands = [b for b in settings.brands if b.lower().replace(" ", "") not in excluded]
    skipped = [b for b in settings.brands if b not in brands]

    # fetch everything once (cached sources make repeat cycles cheap)
    fetched: dict[str, list[Item]] = {}
    for src in sources:
        status = getattr(src, "warmup", lambda: None)()
        items: list[Item] = []
        for brand in brands:
            try:
                items.extend(i for i in src.fetch_brand(brand)
                             if not is_blocked(i, blacklist, settings.excluded_brands))
            except Exception as exc:  # one failing site/brand must not kill the cycle
                echo(f"  [{src.name}] {brand}: 수집 실패 ({exc})")
        fetched[src.name] = items
        src._warmup_status = status

    # STEP 0 — 자판기 1: 신규/가격하락 감지
    detect_sources = [s for s in sources if getattr(s, "detect", False)]
    echo(f"\n[STEP 0] 신규 상품 감지 / 대상 브랜드: {len(brands)}개")
    if skipped:
        echo(f"  [신규감지] 수동매핑 브랜드 제외: {', '.join(skipped)}")
    for src in detect_sources:
        baseline = not db.has_source(src.name)
        echo(f"  [{src.name} 신규감지] 기존 DB: {db.count(src.name):,}개" + (" (첫 실행: 기준선만 저장)" if baseline else ""))
        if src._warmup_status is not None:
            echo(f"  [{src.name} 신규감지] 세션 워밍업 완료 (HTTP {src._warmup_status})")
        evs = detect(fetched[src.name], db, settings.price_drop_threshold, baseline)
        by_brand: dict[str, int] = {}
        for e in evs:
            if e.kind == "new":
                by_brand[e.item.brand] = by_brand.get(e.item.brand, 0) + 1
        for b, n in by_brand.items():
            echo(f"  [{src.name} 신규감지] {b}: {n}개 신규")
        drops = sum(1 for e in evs if e.kind == "price_drop")
        if drops:
            echo(f"  [{src.name} 신규감지] 가격 하락: {drops}개")
        if not evs:
            echo(f"  [{src.name} 신규감지] 신규 상품 없음")
        res.events.extend(evs)
    db.save()
    res.events = [Event(e.kind, e.item, e.prev_price, apply_coupons(e.item.price, settings.coupons))
                  for e in res.events]
    if res.events:
        echo(f"\n[알림] Kick Monitor {len(res.events)}건 전송")
        notifier.send(res.events)

    # STEP 1 — 데이터 로드 요약
    echo("\n[STEP 1] 데이터 로드")
    for src in sources:
        age = getattr(src, "last_hit_age_min", None)
        how = f"캐시 로드 ({age}분 전)" if age is not None else "새로 수집"
        echo(f"  [{src.name}] {how} - {len(fetched[src.name]):,}개")

    # STEP 2 — 자판기 2: 소싱표
    sourcing = [i for s in sources if s.role == "sourcing" for i in fetched[s.name]]
    market = [i for s in sources if s.role == "market" for i in fetched[s.name]]
    stores = sorted({i.store for i in sourcing if i.store})
    echo(f"\n[STEP 2] 소싱처 스캔 시작 - 스토어 {len(stores)}곳 / 소싱 상품 {len(sourcing):,}개 vs 판매 기준 {len(market):,}개")
    res.opportunities = build_opportunities(sourcing, market, settings)
    if res.opportunities:
        res.sheet_path = write_xlsx(res.opportunities, Path(out_dir) / f"sourcing_{datetime.now():%Y%m%d_%H%M}.xlsx")
        echo(f"  마진 {settings.min_margin:,}원 이상: {len(res.opportunities)}개 -> {res.sheet_path}")
        for o in res.opportunities[:10]:
            echo(f"   - {o.brand} {o.style_code} | {o.source}/{o.store} {o.our_cost:,} -> "
                 f"{o.market} {o.sell_price:,} | 마진 {o.margin:,} ({o.margin_rate:.0%})")
    else:
        echo("  조건을 만족하는 품번 없음")

    # STEP 3 — 위탁 판매 상품 감시 (품절 / 마진 소멸)
    if listings:
        from .listings import check_listings

        res.listing_events = check_listings(listings, fetched, settings)
        unlist = sum(1 for e in res.listing_events if e.kind == "unlist")
        check = len(res.listing_events) - unlist
        echo(f"\n[STEP 3] 판매중 상품 {len(listings)}개 감시 - 판매 중지 필요 {unlist}개 / 확인 필요 {check}개")
        if res.listing_events:
            notifier.send(res.listing_events)
    return res
