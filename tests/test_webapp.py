import json

import pytest

from shopping_shorts_sync.webapp import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    products_path = tmp_path / "products.json"
    products_path.write_text("[]", encoding="utf-8")

    monkeypatch.setenv("STATE_FILE_PATH", str(tmp_path / "state.json"))
    monkeypatch.setenv("SCRIPTS_DIR", str(tmp_path / "scripts"))
    monkeypatch.setenv("VIDEO_OUTPUT_DIR", str(tmp_path / "videos"))
    monkeypatch.setenv("COUPANG_API_MODE", "mock")

    app = create_app(products_path=str(products_path))
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_dashboard_empty(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "등록된 상품이 없습니다".encode() in resp.data


def test_search_shows_mock_results(client):
    resp = client.get("/search?keyword=%EB%AC%B4%EC%84%A0%EC%B2%AD%EC%86%8C%EA%B8%B0")
    assert resp.status_code == 200
    assert "naver".encode() in resp.data


def test_full_flow_new_product_through_approve(client):
    resp = client.post(
        "/products/new",
        data={
            "keyword": "무선 청소기",
            "source": "daiso",
            "index": "0",
            "category": "생활용품",
            "target_page": "harujin",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302
    location = resp.headers["Location"]
    assert "/products/" in location

    product_id = location.split("/products/")[1].split("?")[0]

    # dashboard now lists it
    dash = client.get("/")
    assert product_id.encode() in dash.data or "생활용품".encode() in dash.data

    # video step: shows candidates from both youtube + instagram (mock)
    video_page = client.get(f"/products/{product_id}?step=video")
    assert video_page.status_code == 200
    assert "youtube".encode() in video_page.data
    assert "instagram".encode() in video_page.data

    # stitch exactly 3 selected clips (mock)
    stitch_resp = client.post(
        f"/products/{product_id}/video/stitch",
        data={
            "video_url": [
                "https://example.com/youtube/product/1",
                "https://example.com/youtube/product/2",
                "https://example.com/instagram/product/1",
            ]
        },
        follow_redirects=False,
    )
    assert stitch_resp.status_code == 302

    video_done_page = client.get(f"/products/{product_id}?step=video")
    assert "짜깁기 완성".encode() in video_done_page.data

    video_file_resp = client.get(f"/videos/{product_id}/stitched.mp4")
    assert video_file_resp.status_code == 200

    # product/script step -> a script set was auto-generated
    script_page = client.get(f"/products/{product_id}?step=script")
    assert script_page.status_code == 200
    assert "후보 1".encode() in script_page.data

    # select candidate 1
    select_resp = client.post(f"/products/{product_id}/scripts/1/select", follow_redirects=False)
    assert select_resp.status_code == 302
    assert "step=voice" in select_resp.headers["Location"]

    # voice step: generate TTS (mock)
    voice_page = client.get(f"/products/{product_id}?step=voice")
    assert "표준_여성_20-30대".encode() in voice_page.data

    voice_resp = client.post(
        f"/products/{product_id}/voice/generate",
        data={"voice_label": "표준_여성_20-30대"},
        follow_redirects=False,
    )
    assert voice_resp.status_code == 302
    assert "step=hashtags" in voice_resp.headers["Location"]

    voice_done_page = client.get(f"/products/{product_id}?step=voice")
    assert "음성 생성 완료".encode() in voice_done_page.data

    # hashtags step shows disclosure + ad label
    hashtags_page = client.get(f"/products/{product_id}?step=hashtags")
    assert "쿠팡 파트너스".encode() in hashtags_page.data
    assert "[광고]".encode() in hashtags_page.data

    # approve -> also auto-syncs to Inpock (mock)
    approve_resp = client.post(f"/products/{product_id}/approve", follow_redirects=False)
    assert approve_resp.status_code == 302

    approve_page = client.get(f"/products/{product_id}?step=approve")
    assert "승인 완료".encode() in approve_page.data
    assert "인포크 자동 반영 완료".encode() in approve_page.data
    assert "https://link.inpock.co.kr/harujin".encode() in approve_page.data

    dash_page = client.get("/")
    assert "https://link.inpock.co.kr/harujin".encode() in dash_page.data
    assert "https://link.inpock.co.kr/shinjh".encode() in dash_page.data


def test_video_stitch_rejects_wrong_number_of_urls(client):
    resp = client.post(
        "/products/new",
        data={"keyword": "무선 청소기", "source": "daiso", "index": "0", "category": "생활용품", "target_page": "harujin"},
    )
    product_id = resp.headers["Location"].split("/products/")[1].split("?")[0]

    stitch_resp = client.post(
        f"/products/{product_id}/video/stitch",
        data={"video_url": ["https://example.com/a", "https://example.com/b"]},
        follow_redirects=False,
    )
    assert stitch_resp.status_code == 302

    page = client.get(f"/products/{product_id}?step=video")
    assert "짜깁기 완성".encode() not in page.data


def test_approve_without_script_selection_does_not_set_approved(client):
    resp = client.post(
        "/products/new",
        data={
            "keyword": "수분 세럼",
            "source": "naver",
            "index": "0",
            "category": "뷰티",
            "target_page": "shinjh",
        },
    )
    product_id = resp.headers["Location"].split("/products/")[1].split("?")[0]

    client.post(f"/products/{product_id}/approve")
    page = client.get(f"/products/{product_id}?step=approve")
    assert "승인 완료".encode() not in page.data
