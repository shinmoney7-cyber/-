from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from shopping_shorts_sync.models import Product
from shopping_shorts_sync.script_generator import MockScriptGenerator, OpenAIScriptGenerator, build_script_generator
from shopping_shorts_sync.script_store import REQUIRED_CANDIDATE_COUNT, ScriptSet


def _make_product(**kwargs) -> Product:
    defaults = dict(
        id="test-product-01",
        name="테스트 청소기",
        coupang_url="https://www.coupang.com/vp/products/123",
        thumbnail="https://img.example.com/thumb.jpg",
        category="생활용품",
        target_page="harujin",
        enabled=True,
    )
    defaults.update(kwargs)
    return Product(**defaults)


class TestMockScriptGenerator:
    def test_returns_script_set_with_five_candidates(self):
        product = _make_product()
        gen = MockScriptGenerator()
        result = gen.generate(product)
        assert isinstance(result, ScriptSet)
        assert result.product_id == product.id
        assert len(result.candidates) == REQUIRED_CANDIDATE_COUNT

    def test_candidate_ids_are_unique_and_one_indexed(self):
        product = _make_product()
        result = MockScriptGenerator().generate(product)
        ids = [c.id for c in result.candidates]
        assert ids == list(range(1, REQUIRED_CANDIDATE_COUNT + 1))

    def test_all_aida_fields_are_non_empty(self):
        product = _make_product()
        result = MockScriptGenerator().generate(product)
        for c in result.candidates:
            assert c.attention
            assert c.interest
            assert c.desire
            assert c.action

    def test_product_name_interpolated_into_at_least_one_field(self):
        product = _make_product(name="특별한청소기")
        result = MockScriptGenerator().generate(product)
        full_texts = [c.full_text for c in result.candidates]
        assert any("특별한청소기" in t for t in full_texts)

    def test_selected_id_defaults_to_none(self):
        result = MockScriptGenerator().generate(_make_product())
        assert result.selected_id is None


class TestOpenAIScriptGenerator:
    def test_raises_value_error_when_api_key_empty(self):
        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            OpenAIScriptGenerator(api_key="")

    def test_raises_import_error_when_openai_not_installed(self):
        import sys
        with patch.dict(sys.modules, {"openai": None}):
            with pytest.raises(ImportError, match="openai package"):
                OpenAIScriptGenerator(api_key="sk-test")

    def test_calls_openai_and_parses_response(self):
        mock_candidates = [
            {"id": i, "attention": f"att{i}", "interest": f"int{i}", "desire": f"des{i}", "action": f"act{i}"}
            for i in range(1, REQUIRED_CANDIDATE_COUNT + 1)
        ]
        mock_response_content = json.dumps({"candidates": mock_candidates})

        mock_choice = MagicMock()
        mock_choice.message.content = mock_response_content
        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]

        mock_openai_class = MagicMock()
        mock_openai_class.return_value.chat.completions.create.return_value = mock_completion

        with patch("openai.OpenAI", mock_openai_class):
            gen = OpenAIScriptGenerator(api_key="sk-test", model="gpt-4o-mini")
            result = gen.generate(_make_product())

        assert len(result.candidates) == REQUIRED_CANDIDATE_COUNT
        assert result.candidates[0].attention == "att1"

    def test_passes_product_name_in_user_message(self):
        mock_candidates = [
            {"id": i, "attention": "a", "interest": "b", "desire": "c", "action": "d"}
            for i in range(1, REQUIRED_CANDIDATE_COUNT + 1)
        ]
        mock_response_content = json.dumps({"candidates": mock_candidates})
        mock_choice = MagicMock()
        mock_choice.message.content = mock_response_content
        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]

        mock_openai_class = MagicMock()
        mock_create = mock_openai_class.return_value.chat.completions.create
        mock_create.return_value = mock_completion

        product = _make_product(name="고급진세럼")
        with patch("openai.OpenAI", mock_openai_class):
            gen = OpenAIScriptGenerator(api_key="sk-test")
            gen.generate(product)

        call_kwargs = mock_create.call_args
        messages = call_kwargs.kwargs.get("messages") or call_kwargs.args[0]
        user_content = next(m["content"] for m in messages if m["role"] == "user")
        assert "고급진세럼" in user_content


class TestBuildScriptGenerator:
    def test_dry_run_returns_mock(self):
        gen = build_script_generator(api_key="", model="gpt-4o-mini", dry_run=True)
        assert isinstance(gen, MockScriptGenerator)

    def test_live_returns_openai_generator(self):
        mock_openai_class = MagicMock()
        with patch("openai.OpenAI", mock_openai_class):
            gen = build_script_generator(api_key="sk-test", model="gpt-4o-mini", dry_run=False)
        assert isinstance(gen, OpenAIScriptGenerator)
