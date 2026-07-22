"""Mobile-friendly dashboard on top of the real search/Coupang/script
pipeline already built in this package. This is a thin view layer — every
action it triggers (Coupang auto-matching, deeplink generation, AIDA
script generation, state tracking) calls the same functions the CLI uses,
so there is exactly one implementation of each piece of business logic.

Flow mirrors the owner's spec: search -> pick a product -> auto Coupang
link -> pick 3 of up to 15 related videos and auto-stitch a preview ->
auto 5-candidate script -> pick a script candidate -> generate TTS voice
(Typecast) -> hashtags per platform -> final review ("확인키") -> approve.
"""
from __future__ import annotations

import dataclasses
from pathlib import Path

from flask import Flask, redirect, render_template, request, send_from_directory, url_for

from ..config import load_config
from ..input_loader import load_products
from ..inpock.mock_rpa import MockInpockRPAClient
from ..inpock.selectors import PUBLIC_PAGE_URLS
from ..models import Product
from ..script_store import ScriptSet, default_script_path, load_script_set, save_script_set
from ..scriptgen import AD_LABEL, AD_LABEL_POSITION, COUPANG_PARTNERS_DISCLOSURE, generate_candidates, generate_hashtags
from ..search.orchestrator import VIDEO_SOURCES, match_and_upsert_product, search_all_sources, search_one_source
from ..state_store import StateStore
from ..sync import build_coupang_client, run_deeplink_stage, run_inpock_stage
from ..tts import build_tts_client
from ..tts.voices import VOICE_CATALOG, get_voice
from ..video.pipeline import VideoPipelineError, generate_stitched_video

STEPS = [
    ("product", "1. 상품정보"),
    ("video", "2. 영상선택"),
    ("script", "3. 대본선택"),
    ("voice", "4. 음성생성"),
    ("hashtags", "5. 해시태그/배포"),
    ("approve", "6. 최종승인"),
]

CATEGORY_CHOICES = ["뷰티", "생활용품", "육아", "다이어트", "가전"]
TARGET_PAGE_CHOICES = ["harujin", "shinjh"]
DEPLOY_PLATFORMS = [
    ("instagram", "인스타그램"),
    ("threads", "쓰레드"),
    ("youtube", "유튜브"),
    ("tiktok", "틱톡"),
    ("naver_clip", "네이버클립"),
    ("toss", "토스"),
    ("danggeun", "당근마켓"),
    ("naver_blog", "네이버블로그"),
]


def create_app(products_path: str = "data/products.example.json") -> Flask:
    app = Flask(__name__)
    app.config["PRODUCTS_PATH"] = products_path

    def _config():
        return load_config()

    def _state():
        return StateStore(_config().state_file_path)

    def _products() -> dict[str, Product]:
        path = app.config["PRODUCTS_PATH"]
        try:
            return {p.id: p for p in load_products(path)}
        except Exception:
            return {}

    @app.get("/")
    def dashboard():
        products = _products()
        state = _state()
        rows = []
        for product in products.values():
            pstate = state.get(product.id)
            rows.append(
                {
                    "product": product,
                    "deeplink_ready": bool(pstate and pstate.deeplink),
                    "script_selected": bool(pstate and pstate.selected_script_id),
                    "approved": bool(pstate and pstate.approved_at),
                }
            )
        return render_template("dashboard.html", rows=rows, ad_label=AD_LABEL, inpock_pages=PUBLIC_PAGE_URLS)

    @app.get("/search")
    def search():
        keyword = request.args.get("keyword", "").strip()
        results = {}
        if keyword:
            results = search_all_sources(keyword, _config(), dry_run=True, limit=5)
        return render_template(
            "search.html",
            keyword=keyword,
            results=results,
            categories=CATEGORY_CHOICES,
            target_pages=TARGET_PAGE_CHOICES,
        )

    @app.post("/products/new")
    def products_new():
        keyword = request.form["keyword"]
        source = request.form["source"]
        index = int(request.form["index"])
        category = request.form["category"]
        target_page = request.form["target_page"]
        live = request.form.get("live") == "on"
        dry_run = not live

        config = _config()
        if live:
            config = dataclasses.replace(config, coupang_api_mode="live")

        results = search_one_source(source, keyword, config, dry_run=dry_run)
        if index >= len(results):
            return redirect(url_for("search", keyword=keyword))
        selected = results[index]

        product = match_and_upsert_product(
            selected, target_page, category, config, app.config["PRODUCTS_PATH"], dry_run=dry_run
        )
        if product is None:
            return redirect(url_for("search", keyword=keyword))

        script_path = default_script_path(product.id, base_dir=config.scripts_dir)
        if not script_path.exists():
            candidates = generate_candidates(product.name, category)
            save_script_set(script_path, ScriptSet(product_id=product.id, candidates=candidates))

        state = _state()
        client = build_coupang_client(config)
        run_deeplink_stage([product], client, state, force=True)
        state.save()

        return redirect(url_for("product_detail", product_id=product.id, step="product"))

    @app.get("/products/<product_id>")
    def product_detail(product_id):
        products = _products()
        product = products.get(product_id)
        if product is None:
            return redirect(url_for("dashboard"))

        step = request.args.get("step", "product")
        if step not in {s for s, _ in STEPS}:
            step = "product"
        step_index = [s for s, _ in STEPS].index(step)
        prev_step = STEPS[step_index - 1][0] if step_index > 0 else None
        next_step = STEPS[step_index + 1][0] if step_index < len(STEPS) - 1 else None

        state = _state()
        pstate = state.get(product_id)

        script_path = default_script_path(product_id, base_dir=_config().scripts_dir)
        script_set = load_script_set(script_path) if script_path.exists() else None

        hashtags = generate_hashtags(product.name, product.category)

        video_results = {}
        if step == "video":
            config = _config()
            per_source_limits = {"youtube": 8, "instagram": 7}  # 총 15개
            for source in VIDEO_SOURCES:
                video_results[source] = search_one_source(
                    source, product.name, config, dry_run=True, limit=per_source_limits[source]
                )

        return render_template(
            "product.html",
            product=product,
            pstate=pstate,
            script_set=script_set,
            steps=STEPS,
            step=step,
            prev_step=prev_step,
            next_step=next_step,
            hashtags=hashtags,
            platforms=DEPLOY_PLATFORMS,
            disclosure=COUPANG_PARTNERS_DISCLOSURE,
            ad_label=AD_LABEL,
            ad_label_position=AD_LABEL_POSITION,
            voices=VOICE_CATALOG,
            inpock_pages=PUBLIC_PAGE_URLS,
            video_results=video_results,
        )

    @app.post("/products/<product_id>/video/stitch")
    def video_stitch(product_id):
        products = _products()
        product = products.get(product_id)
        if product is None:
            return redirect(url_for("dashboard"))

        urls = [u for u in request.form.getlist("video_url") if u]
        live = request.form.get("live") == "on"

        if len(urls) != 3:
            return redirect(url_for("product_detail", product_id=product_id, step="video"))

        config = _config()
        config = dataclasses.replace(config, video_mode="live" if live else "mock")

        try:
            output_path = generate_stitched_video(urls, product_id, config)
        except VideoPipelineError:
            return redirect(url_for("product_detail", product_id=product_id, step="video"))

        state = _state()
        state.record_video(product_id, str(output_path), urls)
        state.save()

        return redirect(url_for("product_detail", product_id=product_id, step="video"))

    @app.get("/videos/<product_id>/<filename>")
    def serve_video(product_id, filename):
        video_dir = Path(_config().video_output_dir) / product_id
        return send_from_directory(video_dir, filename)

    @app.post("/products/<product_id>/scripts/generate")
    def script_generate(product_id):
        products = _products()
        product = products.get(product_id)
        if product is None:
            return redirect(url_for("dashboard"))

        script_path = default_script_path(product_id, base_dir=_config().scripts_dir)
        candidates = generate_candidates(product.name, product.category)
        save_script_set(script_path, ScriptSet(product_id=product_id, candidates=candidates))
        return redirect(url_for("product_detail", product_id=product_id, step="script"))

    @app.post("/products/<product_id>/scripts/<int:candidate_id>/select")
    def script_select(product_id, candidate_id):
        products = _products()
        product = products.get(product_id)
        if product is None:
            return redirect(url_for("dashboard"))

        script_path = default_script_path(product_id, base_dir=_config().scripts_dir)
        script_set = load_script_set(script_path)
        candidate = script_set.select(candidate_id)
        save_script_set(script_path, script_set)

        state = _state()
        state.apply_script(product, candidate.id, candidate.full_text)
        state.save()

        return redirect(url_for("product_detail", product_id=product_id, step="voice"))

    @app.post("/products/<product_id>/voice/generate")
    def voice_generate(product_id):
        voice_label = request.form["voice_label"]
        live = request.form.get("live") == "on"

        config = _config()
        config = dataclasses.replace(config, typecast_mode="live" if live else "mock")

        state = _state()
        pstate = state.get(product_id)
        if pstate is None or not pstate.script_text:
            return redirect(url_for("product_detail", product_id=product_id, step="script"))

        actor_id = get_voice(voice_label).actor_id
        client = build_tts_client(config)
        result = client.synthesize(pstate.script_text, actor_id=actor_id, speed=config.typecast_speed)
        state.record_voice(product_id, result.audio_url, actor_id)
        state.save()

        return redirect(url_for("product_detail", product_id=product_id, step="hashtags"))

    @app.post("/products/<product_id>/approve")
    def approve(product_id):
        products = _products()
        product = products.get(product_id)
        if product is None:
            return redirect(url_for("dashboard"))

        state = _state()
        try:
            state.approve(product)
        except ValueError:
            state.save()
            return redirect(url_for("product_detail", product_id=product_id, step="approve"))

        # "확인키" 승인 = 배포 준비 완료 -> 인포크 링크 카드에 자동 반영.
        # 실제 브라우저 로그인(--live)은 CALIBRATION 전이라 기본은 mock.
        live = request.form.get("live") == "on"
        config = _config()
        if live:
            from ..browser import launch_browser
            from ..inpock.rpa import InpockRPAClient

            with launch_browser(
                headless=config.inpock_headless, chromium_path=config.playwright_chromium_path
            ) as browser:
                page = browser.new_page()
                rpa_client = InpockRPAClient(page, config.inpock_email, config.inpock_password)
                rpa_client.login()
                run_inpock_stage([product], rpa_client, state, force_create=False)
        else:
            run_inpock_stage([product], MockInpockRPAClient(), state, force_create=False)

        state.save()
        return redirect(url_for("product_detail", product_id=product_id, step="approve"))

    @app.post("/products/<product_id>/unapprove")
    def unapprove(product_id):
        state = _state()
        state.unapprove(product_id)
        state.save()
        return redirect(url_for("product_detail", product_id=product_id, step="approve"))

    return app
