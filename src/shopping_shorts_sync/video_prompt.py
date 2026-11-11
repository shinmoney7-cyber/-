"""Convert Product + ScriptCandidate into 6-scene video prompts for Higgsfield / TopView."""
from __future__ import annotations

from dataclasses import dataclass, field

from .models import Product
from .script_store import ScriptCandidate

# Duration ratios for each scene (summing to 1.0), following the standard 6-step structure.
SCENE_RATIOS = [
    ("후킹",     0.00, 0.08),
    ("문제공감",  0.08, 0.20),
    ("제품등장",  0.20, 0.48),
    ("베네핏",   0.48, 0.72),
    ("신뢰요소",  0.72, 0.88),
    ("CTA",     0.88, 1.00),
]

CATEGORY_ENV = {
    "욕실": "Korean bathroom, white tiles, morning light",
    "청소": "Korean living room, daylight, wooden floor",
    "주방": "Korean kitchen, modern countertop, natural light",
    "뷰티": "Korean vanity table, soft ring-light, mirror close-up",
    "스킨케어": "Korean vanity table, soft ring-light, mirror close-up",
    "건강": "Korean home, gym mat, morning light",
    "헬스": "Korean home, gym mat, morning light",
    "IT": "Korean desk, clean workspace, monitor glow",
    "가전": "Korean living room, modern furniture, clean backdrop",
    "육아": "Korean children's room, pastel colors, safe and warm",
    "패션": "Korean urban street, natural daylight, casual chic backdrop",
    "잡화": "Korean urban street, natural daylight, casual chic backdrop",
    "식품": "Korean kitchen counter, wooden cutting board, fresh herbs",
    "신선식품": "Korean kitchen counter, wooden cutting board, fresh ingredients",
}


def _env_for_category(category: str) -> str:
    for key, env in CATEGORY_ENV.items():
        if key in category:
            return env
    return "Korean modern home interior, clean and bright"


@dataclass
class ScenePrompt:
    scene_num: int
    label: str          # 후킹, 문제공감, 제품등장, 베네핏, 신뢰요소, CTA
    start_sec: float
    end_sec: float
    visual_prompt: str  # English prompt for AI video model
    subtitle: str       # Korean subtitle / dialogue line
    camera: str         # camera direction note


@dataclass
class VideoPromptSet:
    product_id: str
    candidate_id: int
    product_name: str
    category: str
    duration_sec: int
    scenes: list[ScenePrompt] = field(default_factory=list)

    def as_single_prompt(self) -> str:
        """Concatenated English prompt for single-shot text-to-video models."""
        parts = [f"[{s.label}] {s.visual_prompt}" for s in self.scenes]
        return " | ".join(parts)

    def higgsfield_prompt(self) -> str:
        """Full English narrative prompt optimised for Higgsfield."""
        lines = [
            f"Korean-style vertical short-form shopping video ({self.duration_sec}s), 9:16 ratio.",
            f"Product: {self.product_name}.",
            "Hands and arms only visible (no face), POV-style, authentic Korean home environment.",
            "",
        ]
        for s in self.scenes:
            lines.append(
                f"Scene {s.scene_num} ({s.label}, {s.start_sec:.0f}-{s.end_sec:.0f}s): "
                f"{s.visual_prompt}. Camera: {s.camera}. Subtitle: '{s.subtitle}'."
            )
        return "\n".join(lines)


def build_prompt_set(
    product: Product,
    candidate: ScriptCandidate,
    duration_sec: int = 25,
) -> VideoPromptSet:
    env = _env_for_category(product.category)
    name = product.name

    # Map AIDA stages to the 6 visual scenes
    scene_configs = [
        # (label, visual_description, subtitle, camera)
        (
            "후킹",
            f"Close-up of a person's hand reacting to a messy or problematic situation in {env}. "
            f"Surprised reaction, problem is visible. Dark/dim mood.",
            candidate.attention,
            "Extreme close-up, slight camera shake, 1-second hold",
        ),
        (
            "문제공감",
            f"Extreme close-up repeating and amplifying the problem situation in {env}. "
            f"Slow zoom in, frustration implied without showing face.",
            candidate.attention,
            "Macro close-up, slow push-in",
        ),
        (
            "제품등장",
            f"Hand picks up {name} packaging from a surface in {env}. "
            f"Product label clearly visible. Quick cut to usage demonstration. "
            f"Bright lighting shift to indicate solution. "
            f"Interest point: {candidate.interest}",
            candidate.interest,
            "Medium close-up panning to product, then to hands using it",
        ),
        (
            "베네핏",
            f"Before-and-after split or time-lapse showing visible benefit of using {name} in {env}. "
            f"Result is clearly visible. Satisfying transformation. "
            f"Context: {candidate.desire}",
            candidate.desire,
            "Wide angle capturing full result area, natural light",
        ),
        (
            "신뢰요소",
            f"Close-up of {name} packaging with review star overlay and sales count text. "
            f"Hands rotate product. Clean {env} background.",
            "리뷰 ★★★★★  재구매 98%",
            "Slow 360° rotation, overlay text animates in",
        ),
        (
            "CTA",
            f"Final shot: {name} prominently displayed with price tag visible in {env}. "
            f"Hand points toward screen / camera. Bright, high-energy finish.",
            candidate.action,
            "Pull-back to show product and hand gesture toward viewer",
        ),
    ]

    scenes: list[ScenePrompt] = []
    for i, (ratio_label, ratio_start, ratio_end) in enumerate(SCENE_RATIOS):
        label, visual, subtitle, camera = scene_configs[i]
        start = round(ratio_start * duration_sec, 1)
        end = round(ratio_end * duration_sec, 1)
        scenes.append(
            ScenePrompt(
                scene_num=i + 1,
                label=label,
                start_sec=start,
                end_sec=end,
                visual_prompt=visual,
                subtitle=subtitle,
                camera=camera,
            )
        )

    return VideoPromptSet(
        product_id=product.id,
        candidate_id=candidate.id,
        product_name=name,
        category=product.category,
        duration_sec=duration_sec,
        scenes=scenes,
    )
