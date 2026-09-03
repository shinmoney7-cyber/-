import pytest

from shopping_shorts_sync.tts.mock_client import MockTypecastClient
from shopping_shorts_sync.tts.typecast_client import SPEAK_ENDPOINT, TypecastApiError, TypecastClient
from shopping_shorts_sync.tts.voices import VOICE_CATALOG, get_voice


def test_voice_catalog_has_exactly_20_entries():
    assert len(VOICE_CATALOG) == 20


def test_only_standard_female_20s_is_calibrated():
    calibrated = [v for v in VOICE_CATALOG if v.calibrated]
    assert len(calibrated) == 1
    assert calibrated[0].label == "표준_여성_20-30대"
    assert calibrated[0].actor_id == "예슬"


def test_get_voice_unknown_label_raises():
    with pytest.raises(KeyError):
        get_voice("존재하지않는보이스")


def test_mock_client_deterministic():
    client = MockTypecastClient()
    a = client.synthesize("안녕하세요", actor_id="예슬")
    b = client.synthesize("안녕하세요", actor_id="예슬")
    assert a.audio_url == b.audio_url
    assert a.actor_id == "예슬"


def test_mock_client_differs_by_text():
    client = MockTypecastClient()
    a = client.synthesize("안녕하세요", actor_id="예슬")
    b = client.synthesize("다른 텍스트", actor_id="예슬")
    assert a.audio_url != b.audio_url


def test_missing_api_key_raises():
    with pytest.raises(TypecastApiError):
        TypecastClient(api_key="")


def test_synthesize_direct_response(requests_mock):
    requests_mock.post(SPEAK_ENDPOINT, json={"result": {"audio_download_url": "https://typecast.ai/audio/x.mp3"}})
    client = TypecastClient(api_key="key")
    result = client.synthesize("안녕하세요", actor_id="예슬")
    assert result.audio_url == "https://typecast.ai/audio/x.mp3"
    assert result.actor_id == "예슬"


def test_synthesize_polls_until_done(requests_mock, monkeypatch):
    monkeypatch.setattr("shopping_shorts_sync.tts.typecast_client.time.sleep", lambda _seconds: None)
    poll_url = "https://typecast.ai/api/speak/job123"
    requests_mock.post(SPEAK_ENDPOINT, json={"result": {"speak_v2_url": poll_url}})
    requests_mock.get(
        poll_url,
        [
            {"json": {"result": {"status": "progress"}}},
            {"json": {"result": {"status": "done", "audio_download_url": "https://typecast.ai/audio/y.mp3"}}},
        ],
    )
    client = TypecastClient(api_key="key")
    result = client.synthesize("안녕하세요", actor_id="예슬")
    assert result.audio_url == "https://typecast.ai/audio/y.mp3"


def test_synthesize_raises_on_failed_status(requests_mock):
    poll_url = "https://typecast.ai/api/speak/job123"
    requests_mock.post(SPEAK_ENDPOINT, json={"result": {"speak_v2_url": poll_url}})
    requests_mock.get(poll_url, json={"result": {"status": "failed"}})
    client = TypecastClient(api_key="key")
    with pytest.raises(TypecastApiError):
        client.synthesize("안녕하세요", actor_id="예슬")
