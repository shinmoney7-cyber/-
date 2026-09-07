"""End-to-end trending product → script → video pipeline."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from .models import TrendPeriod, KoreaMatch
from .tiktok_fetcher import TikTokTrendFetcher
from .korea_mapper import KoreaMapper

log = logging.getLogger(__name__)


@dataclass
class TrendPipelineResult:
    matches: list[KoreaMatch] = field(default_factory=list)
    scripts_generated: int = 0
    videos_queued: int = 0

    def summary(self) -> str:
        lines = [f"트렌딩 파이프라인 결과: {len(self.matches)}개 상품"]
        for m in self.matches:
            period = m.trending.period.value
            sold = f"{m.trending.sold_count:,}"
            price = f"{m.local_price_krw:,}원" if m.local_price_krw else "가격 미상"
            lines.append(
                f"  [{period} #{m.trending.rank}] {m.local_product_name} "
                f"({m.trending.brand}) | {sold}개 판매 | {price}"
            )
            if m.script_ko:
                lines.append(f"    대본: {m.script_ko[:60]}...")
            platforms = ", ".join(m.available_platforms)
            lines.append(f"    플랫폼: {platforms}")
        lines.append(f"대본 생성: {self.scripts_generated}개 | 영상 큐: {self.videos_queued}개")
        return "\n".join(lines)


class TrendPipeline:
    """Orchestrate: fetch → map → script → (video)."""

    def __init__(self, script_ai=None, video_pipeline=None, mock: bool = True):
        self.fetcher = TikTokTrendFetcher(mock=mock)
        self.mapper = KoreaMapper()
        self.script_ai = script_ai
        self.video_pipeline = video_pipeline

    def run(
        self,
        periods: list[TrendPeriod] | None = None,
        top_n: int = 10,
        generate_scripts: bool = True,
        generate_videos: bool = False,
    ) -> TrendPipelineResult:
        periods = periods or [TrendPeriod.DAY_7, TrendPeriod.DAY_30, TrendPeriod.DAY_365]
        result = TrendPipelineResult()

        log.info("Fetching trending products for periods: %s", [p.value for p in periods])
        products = self.fetcher.fetch(periods=periods, top_n=top_n)
        log.info("Fetched %d trending products", len(products))

        result.matches = self.mapper.map_all(products)

        if generate_scripts and self.script_ai:
            for match in result.matches:
                try:
                    script = self.script_ai.generate_desire_script_15s(
                        product_name=match.trending.name,
                        brand=match.trending.brand,
                        category=match.trending.category,
                        sold_count=match.trending.sold_count,
                        sold_period=match.trending.period.value,
                        local_name=match.local_product_name,
                        local_price_krw=match.local_price_krw,
                    )
                    match.script_ko = script
                    result.scripts_generated += 1

                    tags = self.script_ai.generate_hashtags(
                        match.local_product_name,
                        match.trending.category,
                    )
                    match.hashtags = tags
                except Exception as exc:
                    log.error("Script failed for %s: %s", match.trending.name, exc)

        if generate_videos and self.video_pipeline:
            for match in result.matches:
                if not match.script_ko:
                    continue
                try:
                    self.video_pipeline.generate_product_video(
                        product_name=match.local_product_name,
                        script_text=match.script_ko,
                        thumbnail_url=match.trending.thumbnail_url,
                    )
                    result.videos_queued += 1
                except Exception as exc:
                    log.error("Video failed for %s: %s", match.trending.name, exc)

        return result
