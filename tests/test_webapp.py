import json

import pytest

from shopping_shorts_sync.webapp import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    products_path = tmp_path / "products.json"
    products_path.write_text("[]", encoding="utf-8")

    monkeypatch.setenv("STATE_FILE_PATH", str(tmp_path / "state.json"))
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

    # product/script step -> a script set was auto-generated
    script_page = client.get(f"/products/{product_id}?step=script")
    assert script_page.status_code == 200
    assert "후보 1".encode() in script_page.data

    # select candidate 1
    select_resp = client.post(f"/products/{product_id}/scripts/1/select", follow_redirects=False)
    assert select_resp.status_code == 302

    # hashtags step shows disclosure + ad label
    hashtags_page = client.get(f"/products/{product_id}?step=hashtags")
    assert "쿠팡 파트너스".encode() in hashtags_page.data
    assert "[광고]".encode() in hashtags_page.data

    # approve
    approve_resp = client.post(f"/products/{product_id}/approve", follow_redirects=False)
    assert approve_resp.status_code == 302

    approve_page = client.get(f"/products/{product_id}?step=approve")
    assert "승인 완료".encode() in approve_page.data


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
