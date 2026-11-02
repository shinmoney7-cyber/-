"""run_all: one automation cycle, logging in the same STEP format as the demo."""
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
    opportunities: list[Opportunity] = field(default_factory=list)
    sheet_path: Path | None = None


def run_cycle(settings: VendingSettings, sourcing_sources, store_sources, db: SeenDB,
              blacklist: set[str], notifier, out_dir: str | Path, echo=print) -> CycleResult:
    res = CycleResult()
    line = "=" * 60
    warn = coupon_warning(settings.coupons, settings.conservative_coupons)
    echo(f"[쿠폰률] {coupon_label(settings.coupons)}" + (f"  ⚠ {warn}" if warn else ""))
    echo(line)
    echo(f"  자동화 사이클 시작: {datetime.now():%Y-%m-%d %H:%M}")
    echo(f"  블랙리스트: {len(blacklist)}개 상품번호 로드")
    echo(line)

    brands = [b for b in settings.brands if b.lower().replace(" ", "") not in
              {x.replace(" ", "") for x in settings.excluded_brands}]
    skipped = [b for b in settings.brands if b not in brands]

    # STEP 0 + 1: fetch every sourcing site per brand, detect new / price drops
    all_sourcing: list[Item] = []
    echo(f"\n[STEP 0] 신규 상품 감지 / 대상 브랜드: {len(brands)}개")
    if skipped:
        echo(f"  [신규감지] 수동매핑 브랜드 제외: {', '.join(skipped)}")
    for src in sourcing_sources:
        baseline = not db.has_source(src.name)
        echo(f"  [{src.name} 신규감지] 기존 DB: {db.count(src.name):,}개" + (" (첫 실행: 기준선만 저장)" if baseline else ""))
        status = getattr(src, "warmup", lambda: None)()
        if status is not None:
            echo(f"  [{src.name} 신규감지] 세션 워밍업 완료 (HTTP {status})")
        src_events: list[Event] = []
        for brand in brands:
            try:
                items = [i for i in src.fetch_brand(brand) if not is_blocked(i, blacklist, settings.excluded_brands)]
            except Exception as exc:  # one failing site/brand must not kill the cycle
                echo(f"  [{src.name}] {brand}: 수집 실패 ({exc})")
                continue
            age = getattr(src, "last_hit_age_min", None)
            all_sourcing.extend(items)
            evs = detect(items, db, settings.price_drop_threshold, baseline)
            new = sum(1 for e in evs if e.kind == "new")
            if new:
                echo(f"  [{src.name} 신규감지] {brand}: {new}개 신규" + (f" (캐시 {age}분 전)" if age is not None else ""))
            src_events.extend(evs)
        if not src_events:
            echo(f"  [{src.name} 신규감지] 신규/가격변동 없음")
        res.events.extend(src_events)

    res.events = [Event(e.kind, e.item, e.prev_price, apply_coupons(e.item.price, settings.coupons))
                  for e in res.events]
    db.save()
    if res.events:
        echo(f"\n[알림] {len(res.events)}건 전송")
        notifier.send(res.events)

    # STEP 2: scan competitor 직구 stores and build the 품번 소싱표
    if store_sources:
        echo(f"\n[STEP 2] 네이버 직구 스토어 {len(store_sources)}개 소스 스캔 시작")
        store_items: list[Item] = []
        for src in store_sources:
            for brand in brands:
                try:
                    store_items.extend(src.fetch_brand(brand))
                except Exception as exc:
                    echo(f"  [{src.name}] {brand}: 수집 실패 ({exc})")
        echo(f"  경쟁 상품 {len(store_items):,}개 / 소싱 상품 {len(all_sourcing):,}개 품번 매칭")
        res.opportunities = build_opportunities(all_sourcing, store_items, settings)
        if res.opportunities:
            res.sheet_path = write_xlsx(res.opportunities,
                                        Path(out_dir) / f"sourcing_{datetime.now():%Y%m%d_%H%M}.xlsx")
            echo(f"  마진 {settings.min_margin:,}원 이상: {len(res.opportunities)}개 -> {res.sheet_path}")
        else:
            echo("  조건을 만족하는 품번 없음")
    return res

