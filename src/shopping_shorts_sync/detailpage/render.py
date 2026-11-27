from __future__ import annotations

import html
import shutil
from dataclasses import dataclass
from pathlib import Path

from .spec import DetailPageSpec, check_images_exist

PAGE_WIDTH_PX = 800

_CSS = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
body { margin: 0; background: #f4f4f2; color: #1c1c1c;
  font-family: "Noto Sans KR", "Apple SD Gothic Neo", "Malgun Gothic", sans-serif; }
.page { width: %(width)dpx; margin: 0 auto; background: #fff; }
.hero { padding: 48px 40px 36px; text-align: center; border-bottom: 1px solid #eee; }
.brand { font-size: 15px; color: #888; letter-spacing: .04em; }
.name { font-size: 30px; font-weight: 700; margin: 10px 0 14px; line-height: 1.3; }
.headline { font-size: 18px; color: #444; line-height: 1.6; margin: 0; }
.price { margin-top: 22px; font-size: 26px; font-weight: 700; }
.section { padding: 40px; }
.section + .section { border-top: 1px solid #eee; }
.section h2 { font-size: 22px; margin: 0 0 20px; }
.colorway { margin-bottom: 28px; }
.colorway h3 { font-size: 16px; margin: 0 0 12px; color: #333; }
.grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }
.grid img { width: 100%%; height: auto; display: block; background: #f0f0f0; }
.feature { margin-bottom: 32px; }
.feature img { width: 100%%; display: block; margin-bottom: 14px; }
.feature h3 { font-size: 19px; margin: 0 0 8px; }
.feature p { margin: 0; font-size: 16px; line-height: 1.7; color: #444; }
table.size { width: 100%%; border-collapse: collapse; font-size: 15px; text-align: center; }
table.size th, table.size td { border: 1px solid #e3e3e3; padding: 10px 6px; }
table.size th { background: #fafafa; font-weight: 600; }
.material { font-size: 16px; color: #333; margin: 0 0 16px; }
.notices { margin: 0; padding-left: 20px; font-size: 14px; color: #666; line-height: 1.8; }
.cta { padding: 40px; text-align: center; background: #fff; }
.cta a { display: inline-block; min-width: 280px; padding: 18px 28px; border-radius: 6px;
  background: #1c1c1c; color: #fff; font-size: 18px; font-weight: 700; text-decoration: none; }
@media (max-width: 600px) {
  .page { width: 100%%; }
  .hero, .section, .cta { padding: 28px 16px; }
  .name { font-size: 24px; }
}
"""


@dataclass(frozen=True)
class BuildResult:
    html_path: Path
    asset_dir: Path


def _e(text: str) -> str:
    return html.escape(text, quote=True)


def _asset_name(index: int, source: Path) -> str:
    return f"{index:02d}_{source.name}"


def render_html(spec: DetailPageSpec, asset_map: dict[str, str]) -> str:
    """Build the page markup. `asset_map` maps a spec-relative image path to the path used in HTML."""
    parts: list[str] = []
    parts.append('<div class="page">')

    # Hero
    parts.append('<header class="hero">')
    if spec.brand:
        parts.append(f'<div class="brand">{_e(spec.brand)}</div>')
    parts.append(f'<h1 class="name">{_e(spec.name)}</h1>')
    parts.append(f'<p class="headline">{_e(spec.headline)}</p>')
    if spec.price is not None:
        parts.append(f'<div class="price">{spec.price:,}원</div>')
    parts.append("</header>")

    # Colorway gallery
    parts.append('<section class="section">')
    parts.append("<h2>컬러별 착용컷</h2>")
    for cw in spec.colorways:
        parts.append('<div class="colorway">')
        parts.append(f"<h3>{_e(cw.name)}</h3>")
        parts.append('<div class="grid">')
        for img in cw.images:
            parts.append(f'<img src="{_e(asset_map[img])}" alt="{_e(spec.name)} {_e(cw.name)}" loading="lazy">')
        parts.append("</div></div>")
    parts.append("</section>")

    # Features
    if spec.features:
        parts.append('<section class="section">')
        for f in spec.features:
            parts.append('<div class="feature">')
            if f.image:
                parts.append(f'<img src="{_e(asset_map[f.image])}" alt="{_e(f.title)}" loading="lazy">')
            parts.append(f"<h3>{_e(f.title)}</h3>")
            parts.append(f"<p>{_e(f.body)}</p>")
            parts.append("</div>")
        parts.append("</section>")

    # Size + material
    if spec.size_table or spec.material:
        parts.append('<section class="section">')
        parts.append("<h2>사이즈 & 소재</h2>")
        if spec.material:
            parts.append(f'<p class="material">혼용률 · {_e(spec.material)}</p>')
        if spec.size_table:
            st = spec.size_table
            parts.append('<table class="size"><thead><tr>')
            parts.extend(f"<th>{_e(h)}</th>" for h in st.headers)
            parts.append("</tr></thead><tbody>")
            for row in st.rows:
                parts.append("<tr>" + "".join(f"<td>{_e(c)}</td>" for c in row) + "</tr>")
            parts.append("</tbody></table>")
        parts.append("</section>")

    # Notices
    if spec.notices:
        parts.append('<section class="section">')
        parts.append("<h2>유의사항</h2>")
        parts.append('<ul class="notices">')
        parts.extend(f"<li>{_e(n)}</li>" for n in spec.notices)
        parts.append("</ul></section>")

    # CTA
    if spec.cta_url:
        parts.append(f'<section class="cta"><a href="{_e(spec.cta_url)}">{_e(spec.cta_text)}</a></section>')

    parts.append("</div>")
    body = "\n".join(parts)
    css = _CSS % {"width": PAGE_WIDTH_PX}
    return (
        "<!doctype html>\n"
        '<html lang="ko"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{_e(spec.name)}</title>"
        f"<style>{css}</style></head>\n<body>\n{body}\n</body></html>\n"
    )


def build_detail_page(spec: DetailPageSpec, out_dir: str | Path) -> BuildResult:
    """Copy images into out_dir/assets, write out_dir/index.html. Returns the written paths."""
    check_images_exist(spec)
    out_dir = Path(out_dir)
    asset_dir = out_dir / "assets"
    asset_dir.mkdir(parents=True, exist_ok=True)

    asset_map: dict[str, str] = {}
    counter = 0
    for rel in [img for cw in spec.colorways for img in cw.images] + [
        f.image for f in spec.features if f.image
    ]:
        if rel in asset_map:
            continue
        counter += 1
        source = spec.base_dir / rel
        name = _asset_name(counter, source)
        shutil.copyfile(source, asset_dir / name)
        asset_map[rel] = f"assets/{name}"

    html_path = out_dir / "index.html"
    html_path.write_text(render_html(spec, asset_map), encoding="utf-8")
    return BuildResult(html_path=html_path, asset_dir=asset_dir)
