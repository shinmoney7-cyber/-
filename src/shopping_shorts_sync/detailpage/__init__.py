from .render import BuildResult, build_detail_page, render_html
from .spec import DetailPageSpec, DetailPageSpecError, load_detail_spec

__all__ = [
    "BuildResult",
    "DetailPageSpec",
    "DetailPageSpecError",
    "build_detail_page",
    "load_detail_spec",
    "render_html",
]
