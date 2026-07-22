from shopping_shorts_sync.script_store import REQUIRED_CANDIDATE_COUNT, ScriptSet
from shopping_shorts_sync.scriptgen import (
    AD_LABEL,
    AD_LABEL_POSITION,
    COUPANG_PARTNERS_DISCLOSURE,
    generate_candidates,
    generate_hashtags,
)


def test_generates_exactly_five_candidates():
    candidates = generate_candidates("무선 청소기 XYZ", "가전")
    assert len(candidates) == REQUIRED_CANDIDATE_COUNT


def test_candidates_form_a_valid_script_set():
    # ScriptSet.__post_init__ enforces exactly 5, unique ids -- reuse it as
    # the validation contract for generated output too.
    candidates = generate_candidates("무선 청소기 XYZ", "가전")
    script_set = ScriptSet(product_id="x", candidates=candidates)
    assert [c.id for c in script_set.candidates] == [1, 2, 3, 4, 5]


def test_deterministic_same_inputs_same_output():
    a = generate_candidates("수분 세럼 ABC", "뷰티")
    b = generate_candidates("수분 세럼 ABC", "뷰티")
    assert [c.full_text for c in a] == [c.full_text for c in b]


def test_each_candidate_tagged_with_a_technique():
    candidates = generate_candidates("수분 세럼 ABC", "뷰티")
    techniques = [c.technique for c in candidates]
    assert all(techniques)
    assert techniques[0] == "desire"  # base desire always leads


def test_family_narrative_prioritized_for_childcare_category():
    candidates = generate_candidates("아기 물티슈", "육아용품")
    assert "family_narrative" in [c.technique for c in candidates]


def test_product_name_appears_in_every_stage_that_references_it():
    candidates = generate_candidates("무선 청소기 XYZ", "가전")
    for c in candidates:
        assert "무선 청소기 XYZ" in c.attention


def test_unknown_category_falls_back_to_default_desires():
    candidates = generate_candidates("아무 제품", "정체불명카테고리")
    assert len(candidates) == REQUIRED_CANDIDATE_COUNT
    assert all(c.desire for c in candidates)


def test_search_then_click_cta_present_among_action_variants():
    candidates = generate_candidates("무선 청소기 XYZ", "가전")
    actions = " ".join(c.action for c in candidates)
    assert "검색" in actions
    assert "무선 청소기 XYZ" in actions


def test_hashtags_cover_every_platform_and_include_disclosure_tag():
    tags = generate_hashtags("무선 청소기 XYZ", "가전")
    expected_platforms = {
        "instagram", "threads", "youtube", "tiktok",
        "naver_clip", "toss", "danggeun", "naver_blog",
    }
    assert set(tags) == expected_platforms
    for platform_tags in tags.values():
        assert "#쿠팡파트너스" in platform_tags


def test_disclosure_text_is_the_official_coupang_partners_wording():
    assert "쿠팡 파트너스" in COUPANG_PARTNERS_DISCLOSURE
    assert "수수료" in COUPANG_PARTNERS_DISCLOSURE


def test_ad_label_is_fixed_and_top_right():
    assert AD_LABEL == "[광고]"
    assert AD_LABEL_POSITION == "top-right"
