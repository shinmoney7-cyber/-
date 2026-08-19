from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from .images import ImageGenerator, ImageSpec, MockImageGenerator, PillowImageGenerator
from .storage import MockStorage, VideoStorage
from .tts import MockTTSClient, NaverClovaTTS, TTSClient
from .video import FFmpegRenderer, MockVideoRenderer, VideoRenderer

logger = logging.getLogger(__name__)

# 계정별 도입부 톤 정의
ACCOUNT_TONE = {
    "mom_moneytip": "육아·생활 공감과 시간 절약 관점",
    "showpingkkultem": "제품 발견과 기능 시연 관점",
    "haru_moneytip": "가격 대비 가치와 절약 관점",
}

# 카테고리별 인스타 게시 문구 접두어
CATEGORY_EMOJI = {
    "IT": "💻",
    "뷰티": "💄",
    "생활": "🏠",
    "육아": "👶",
    "다이어트/건강": "💪",
    "과일": "🍎",
}


@dataclass
class ProductBrief:
    """대본 생성과 콘텐츠 파이프라인에 필요한 최소 상품 정보."""
    product_id: str
    name: str
    category: str
    hook: str           # 3초 후킹 문구
    problem: str        # 문제 제기/공감
    feature_1: str      # 핵심 기능 1
    feature_2: str      # 핵심 기능 2
    proof: str          # 검증 근거 (사실 확인된 것만)
    cta: str            # CTA 문구
    inpock_url: str     # 확인된 인포크 링크
    disclaimer: str = "이 게시물에는 제휴 링크가 포함될 수 있습니다."


@dataclass
class ContentAssets:
    product_id: str
    tts_path: str                    # MP3 음성 파일
    image_paths: list[str]           # [hook.jpg, mechanism.jpg, proof_cta.jpg]
    video_path: str                  # 1080×1920 MP4
    thumbnail_path: str              # JPEG 썸네일
    video_url: str | None            # 공개 HTTPS URL (업로드 후 채워짐)
    captions: dict[str, str]         # {account_name: 게시 문구}


def build_captions(brief: ProductBrief) -> dict[str, str]:
    """계정별 게시 문구를 생성한다."""
    emoji = CATEGORY_EMOJI.get(brief.category, "🛒")
    base_cta = f"\n\n🔗 상품 링크: {brief.inpock_url}\n{brief.disclaimer}"

    return {
        "mom_moneytip": (
            f"{emoji} 육아하면서 이런 거 필요하더라고요!\n\n"
            f"✅ {brief.feature_1}\n✅ {brief.feature_2}\n\n"
            f"#{brief.category} #{brief.name.replace(' ', '')} #육아꿀템 #생활꿀팁"
            f"{base_cta}"
        ),
        "showpingkkultem": (
            f"{emoji} {brief.hook}\n\n"
            f"📌 {brief.feature_1}\n📌 {brief.feature_2}\n\n"
            f"#{brief.name.replace(' ', '')} #{brief.category}추천 #쇼핑꿀템 #발견"
            f"{base_cta}"
        ),
        "haru_moneytip": (
            f"{emoji} 이 가격에 이 퀄리티?!\n\n"
            f"💰 {brief.feature_1}\n💰 {brief.feature_2}\n\n"
            f"#{brief.category}절약 #가성비 #{brief.name.replace(' ', '')} #하루꿀팁"
            f"{base_cta}"
        ),
    }


def build_script_text(brief: ProductBrief, duration: int = 30) -> str:
    """duration: 15 | 30 | 50 (초)"""
    if duration == 15:
        return (
            f"[Hook 0-3s] {brief.hook}\n"
            f"[Problem 3-7s] {brief.problem}\n"
            f"[Feature 7-12s] {brief.feature_1}\n"
            f"[CTA 12-15s] {brief.cta} 링크는 프로필 바이오에!"
        )
    elif duration == 50:
        return (
            f"[Hook 0-3s] {brief.hook}\n"
            f"[Problem 3-10s] {brief.problem}\n"
            f"[Feature1 10-22s] {brief.feature_1}\n"
            f"[Feature2 22-35s] {brief.feature_2}\n"
            f"[Proof 35-45s] {brief.proof}\n"
            f"[CTA 45-50s] {brief.cta} 링크는 프로필 바이오에!"
        )
    else:  # 30s default
        return (
            f"[Hook 0-3s] {brief.hook}\n"
            f"[Problem 3-8s] {brief.problem}\n"
            f"[Feature1 8-17s] {brief.feature_1}\n"
            f"[Feature2 17-24s] {brief.feature_2}\n"
            f"[CTA 24-30s] {brief.cta} 링크는 프로필 바이오에!"
        )


class ContentPipeline:
    """상품 브리프로부터 영상 자산 전체를 생성한다."""

    def __init__(
        self,
        output_dir: str,
        tts_client: TTSClient,
        image_generator: ImageGenerator,
        video_renderer: VideoRenderer,
        storage: VideoStorage,
    ):
        self._output_dir = output_dir
        self._tts = tts_client
        self._images = image_generator
        self._video = video_renderer
        self._storage = storage

    def _dir(self, product_id: str) -> str:
        d = os.path.join(self._output_dir, product_id)
        os.makedirs(d, exist_ok=True)
        return d

    def run(self, brief: ProductBrief, *, script_duration: int = 30) -> ContentAssets:
        d = self._dir(brief.product_id)
        script_text = build_script_text(brief, script_duration)

        # 1. TTS
        tts_path = os.path.join(d, "voice.mp3")
        self._tts.synthesize(script_text, tts_path)

        # 2. Images (Hook / Mechanism / Proof+CTA)
        specs = [
            ImageSpec(role="hook", headline=brief.hook, body=brief.problem, product_name=brief.name),
            ImageSpec(role="mechanism", headline=brief.feature_1, body=brief.feature_2, product_name=brief.name),
            ImageSpec(role="proof_cta", headline=brief.proof, body=brief.cta, product_name=brief.name),
        ]
        image_paths = []
        for spec in specs:
            path = os.path.join(d, f"img_{spec.role}.jpg")
            self._images.generate(spec, path)
            image_paths.append(path)

        # 3. Video render
        video_path = os.path.join(d, "shorts.mp4")
        self._video.render(image_paths, tts_path, video_path, total_duration=script_duration)

        # 4. Thumbnail
        thumb_path = os.path.join(d, "thumbnail.jpg")
        self._video.extract_thumbnail(video_path, thumb_path)

        # 5. Upload to public HTTPS storage
        filename = f"{brief.product_id}_shorts.mp4"
        video_url = self._storage.upload(video_path, filename)

        # 6. Captions per account
        captions = build_captions(brief)

        return ContentAssets(
            product_id=brief.product_id,
            tts_path=tts_path,
            image_paths=image_paths,
            video_path=video_path,
            thumbnail_path=thumb_path,
            video_url=video_url,
            captions=captions,
        )


def build_pipeline(config, dry_run: bool = True) -> ContentPipeline:
    """Factory: dry_run=True → all mock clients, False → real clients."""
    if dry_run:
        tts = MockTTSClient()
        images = MockImageGenerator()
        video = MockVideoRenderer()
        storage = MockStorage()
    else:
        tts = NaverClovaTTS(
            client_id=config.naver_tts_client_id,
            client_secret=config.naver_tts_client_secret,
            speaker=getattr(config, "naver_tts_speaker", "nara"),
        )
        images = PillowImageGenerator()
        video = FFmpegRenderer()
        bucket_url = config.meta_video_bucket_url
        if not bucket_url:
            raise RuntimeError("META_VIDEO_BUCKET_URL must be set for live mode")
        from .storage import HttpPutStorage
        storage = HttpPutStorage(bucket_url)

    return ContentPipeline(
        output_dir=getattr(config, "content_output_dir", "data/content"),
        tts_client=tts,
        image_generator=images,
        video_renderer=video,
        storage=storage,
    )
