from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from artifact.analyzer import (
    ATTEMPTS_PER_MODEL,
    TEXT_MODELS,
    VISION_MODELS,
    _detect_mime_type,
    analyze_ingredients,
    extract_ingredients_from_image,
)

GOOD_JSON = '{"summary": "Fine.", "flagged": [], "safe_highlights": [], "score": 90}'


def ok(content):
    message = SimpleNamespace(content=content)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)], error=None)


def overloaded():
    return SimpleNamespace(
        choices=None, error={"message": "Service temporarily overloaded", "code": 503}
    )


def fake_client(*responses):
    client = MagicMock()
    client.chat.completions.create.side_effect = list(responses)
    return client


@patch("artifact.analyzer.time.sleep")
@patch("artifact.analyzer.get_client")
def test_analyze_parses_json_wrapped_in_markdown(mock_get_client, mock_sleep):
    mock_get_client.return_value = fake_client(ok(f"```json\n{GOOD_JSON}\n```"))
    result = analyze_ingredients("Aqua, Glycerin")
    assert result["score"] == 90
    mock_sleep.assert_not_called()


@patch("artifact.analyzer.time.sleep")
@patch("artifact.analyzer.get_client")
def test_analyze_retries_when_provider_is_overloaded(mock_get_client, mock_sleep):
    client = fake_client(overloaded(), ok(GOOD_JSON))
    mock_get_client.return_value = client
    assert analyze_ingredients("Aqua")["score"] == 90
    assert client.chat.completions.create.call_count == 2
    mock_sleep.assert_called_once()


@patch("artifact.analyzer.time.sleep")
@patch("artifact.analyzer.get_client")
def test_analyze_retries_on_empty_content(mock_get_client, mock_sleep):
    mock_get_client.return_value = fake_client(ok(""), ok(GOOD_JSON))
    assert analyze_ingredients("Aqua")["score"] == 90


@patch("artifact.analyzer.time.sleep")
@patch("artifact.analyzer.get_client")
def test_analyze_falls_back_to_next_model(mock_get_client, mock_sleep):
    failures = [overloaded() for _ in range(ATTEMPTS_PER_MODEL)]
    client = fake_client(*failures, ok(GOOD_JSON))
    mock_get_client.return_value = client
    assert analyze_ingredients("Aqua")["score"] == 90
    used = [c.kwargs["model"] for c in client.chat.completions.create.call_args_list]
    assert used[0] == TEXT_MODELS[0]
    assert used[-1] == TEXT_MODELS[1]


@patch("artifact.analyzer.time.sleep")
@patch("artifact.analyzer.get_client")
def test_analyze_gives_up_after_all_models_fail(mock_get_client, mock_sleep):
    total = len(TEXT_MODELS) * ATTEMPTS_PER_MODEL
    client = fake_client(*[overloaded() for _ in range(total)])
    mock_get_client.return_value = client
    with pytest.raises(RuntimeError, match="overloaded"):
        analyze_ingredients("Aqua")
    assert client.chat.completions.create.call_count == total


@patch("artifact.analyzer.time.sleep")
@patch("artifact.analyzer.get_client")
def test_extract_ingredients_from_image_returns_clean_text(mock_get_client, mock_sleep):
    client = fake_client(ok("  Aqua, Glycerin \n"))
    mock_get_client.return_value = client
    assert extract_ingredients_from_image(b"\x89PNG fake") == "Aqua, Glycerin"
    sent = client.chat.completions.create.call_args.kwargs["messages"]
    url = sent[0]["content"][1]["image_url"]["url"]
    assert url.startswith("data:image/png;base64,")


@patch("artifact.analyzer.time.sleep")
@patch("artifact.analyzer.get_client")
def test_extract_ingredients_raises_when_all_vision_models_fail(
    mock_get_client, mock_sleep
):
    total = len(VISION_MODELS) * ATTEMPTS_PER_MODEL
    mock_get_client.return_value = fake_client(*[overloaded() for _ in range(total)])
    with pytest.raises(RuntimeError):
        extract_ingredients_from_image(b"fake image")


def test_detect_mime_type():
    assert _detect_mime_type(b"\x89PNG\r\n") == "image/png"
    assert _detect_mime_type(b"RIFF1234WEBPVP8 ") == "image/webp"
    assert _detect_mime_type(b"\xff\xd8\xff") == "image/jpeg"
    assert _detect_mime_type(b"unknown") == "image/jpeg"
