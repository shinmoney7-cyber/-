import json

import pytest
from click.testing import CliRunner

from shopping_shorts_sync.cli import cli
from shopping_shorts_sync.models import Product
from shopping_shorts_sync.script_store import ScriptCandidate
from shopping_shorts_sync.video import HiggsfieldVideoClient, MockVideoClient, TopviewVideoClient, VideoApiError, build_scenes
from shopping_shorts_sync.video.hix import export_hix_pack
from shopping_shorts_sync.video.pipeline import generate_product_video
from shopping_shorts_sync.video.topview import QUERY_PATH, SUBMIT_PATH

PRODUCT = Product(
    id="harujin-vacuum-01",
    name="무선 청소기 XYZ",
    coupang_url="https://www.coupang.com/vp/products/1",
    thumbnail="https://example.com/vacuum.jpg",
    category="가전",
    target_page="harujin",
)
CANDIDATE = ScriptCandidate(id=3, attention="A", interest="I", desire="D", action="C")


def test_build_scenes_one_per_aida_stage():
    scenes = build_scenes(PRODUCT, CANDIDATE)
    assert [s.stage for s in scenes] == ["attention", "interest", "desire", "action"]
    assert [s.caption for s in scenes] == ["A", "I", "D", "C"]
    assert all("9:16" in s.prompt and PRODUCT.name in s.prompt for s in scenes)


def test_mock_pipeline_is_deterministic():
    clips1, err1 = generate_product_video(PRODUCT, CANDIDATE, MockVideoClient("higgsfield"), 5)
    clips2, _ = generate_product_video(PRODUCT, CANDIDATE, MockVideoClient("higgsfield"), 5)
    assert err1 is None
    assert len(clips1) == 4 and all(c["status"] == "completed" for c in clips1)
    assert [c["video_url"] for c in clips1] == [c["video_url"] for c in clips2]


def test_higgsfield_submit_and_poll(requests_mock):
    base = "https://api.higgsfield.ai"
    submit = requests_mock.post(f"{base}/higgsfield-ai/dop/standard", json={"request_id": "r1"})
    requests_mock.get(
        f"{base}/requests/r1/status",
        [
            {"json": {"status": "queued"}},
            {"json": {"status": "completed", "video": {"url": "https://cdn/r1.mp4"}}},
        ],
    )
    client = HiggsfieldVideoClient("k:s", poll_interval=0)
    request_id = client.submit("https://example.com/a.jpg", "prompt", 5)
    job = client.wait(request_id)

    assert submit.last_request.headers["Authorization"] == "Key k:s"
    assert submit.last_request.json() == {"image_url": "https://example.com/a.jpg", "prompt": "prompt", "duration": 5}
    assert job.ok and job.video_url == "https://cdn/r1.mp4"


def test_higgsfield_nsfw_is_failure(requests_mock):
    requests_mock.get("https://api.higgsfield.ai/requests/r2/status", json={"status": "nsfw"})
    job = HiggsfieldVideoClient("k:s").status("r2")
    assert job.status == "failed" and job.error == "nsfw"


def test_higgsfield_requires_credentials():
    with pytest.raises(VideoApiError):
        HiggsfieldVideoClient("")


def test_topview_upload_submit_and_poll(requests_mock, tmp_path):
    base = "https://api.topview.ai"
    image = tmp_path / "thumb.png"
    image.write_bytes(b"png")
    requests_mock.get(
        f"{base}/v1/upload/credential",
        json={"code": "200", "result": {"fileId": "f1", "uploadUrl": "https://s3.example.com/put"}},
    )
    requests_mock.put("https://s3.example.com/put", status_code=200)
    requests_mock.get(f"{base}/v1/upload/check", json={"code": "200", "result": True})
    submit = requests_mock.post(f"{base}{SUBMIT_PATH}", json={"code": "200", "result": {"taskId": "t1"}})
    requests_mock.get(
        f"{base}{QUERY_PATH}",
        [
            {"json": {"code": "200", "result": {"status": "running"}}},
            {"json": {"code": "200", "result": {"status": "success", "videos": [{"status": "success", "filePath": "https://cdn/t1.mp4"}]}}},
        ],
    )
    client = TopviewVideoClient("uid", "key", poll_interval=0)
    file_id = client.prepare_image(str(image))
    task_id = client.submit(file_id, "prompt", 5)
    job = client.wait(task_id)

    assert file_id == "f1"
    headers = submit.last_request.headers
    assert headers["Topview-Uid"] == "uid" and headers["Authorization"] == "Bearer key"
    body = submit.last_request.json()
    assert body["firstFrameFileId"] == "f1" and body["model"] == "Topview Pro" and body["aspectRatio"] == "9:16"
    assert job.ok and job.video_url == "https://cdn/t1.mp4"


def test_topview_error_code_raises(requests_mock):
    requests_mock.post(f"https://api.topview.ai{SUBMIT_PATH}", json={"code": "4100", "message": "Credit not enough"})
    with pytest.raises(VideoApiError, match="4100"):
        TopviewVideoClient("uid", "key").submit("f1", "p", 5)


def test_hix_pack_export(tmp_path):
    md = export_hix_pack(PRODUCT, 3, build_scenes(PRODUCT, CANDIDATE), 5, tmp_path)
    data = json.loads((md.parent / "hix_prompts.json").read_text(encoding="utf-8"))
    assert len(data["scenes"]) == 4 and data["image"] == PRODUCT.thumbnail
    assert "hix.ai/image-to-video" in md.read_text(encoding="utf-8")


def _write_inputs(tmp_path, selected_id):
    products = tmp_path / "products.json"
    products.write_text(json.dumps([{**PRODUCT.__dict__}], ensure_ascii=False), encoding="utf-8")
    script = tmp_path / "script.json"
    candidates = [{"id": i, "attention": "a", "interest": "i", "desire": "d", "action": "c"} for i in range(1, 6)]
    script.write_text(json.dumps({"product_id": PRODUCT.id, "candidates": candidates, "selected_id": selected_id}), encoding="utf-8")
    return products, script


def test_cli_video_generate_dry_run_records_state(tmp_path, monkeypatch):
    monkeypatch.setenv("STATE_FILE_PATH", str(tmp_path / "state.json"))
    products, script = _write_inputs(tmp_path, selected_id=2)
    result = CliRunner().invoke(
        cli,
        ["video", "generate", "--product-id", PRODUCT.id, "--input", str(products), "--file", str(script), "--provider", "topview"],
    )
    assert result.exit_code == 0, result.output
    state = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))["products"][PRODUCT.id]
    assert state["video_provider"] == "topview(mock)" and state["video_script_id"] == 2
    assert len(state["video_clips"]) == 4


def test_cli_video_generate_requires_selected_script(tmp_path, monkeypatch):
    monkeypatch.setenv("STATE_FILE_PATH", str(tmp_path / "state.json"))
    products, script = _write_inputs(tmp_path, selected_id=None)
    result = CliRunner().invoke(
        cli, ["video", "generate", "--product-id", PRODUCT.id, "--input", str(products), "--file", str(script)]
    )
    assert result.exit_code != 0 and "script select" in result.output
