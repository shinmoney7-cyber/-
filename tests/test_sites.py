from shopping_shorts_sync.search.models import SOURCES
from shopping_shorts_sync.search.sites import MALL_SPECS, RPA_SOURCES, build_rpa_client


def test_registry_covers_every_source_exactly_once():
    assert set(SOURCES) == {"naver"} | set(RPA_SOURCES)
    assert len(RPA_SOURCES) == len(set(RPA_SOURCES)) == len(SOURCES) - 1


def test_every_mall_spec_has_keyword_placeholder():
    for source, spec in MALL_SPECS.items():
        assert "{keyword}" in spec.search_url_template, source


def test_build_rpa_client_for_every_rpa_source():
    for source in RPA_SOURCES:
        client = build_rpa_client(source, page=object())
        assert client.source == source


def test_build_rpa_client_rejects_naver():
    import pytest

    with pytest.raises(ValueError):
        build_rpa_client("naver", page=object())
