from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from artifact.analyzer import (
    MAX_ATTEMPTS,
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
def test_analyze_gives_up_after_max_attempts(mock_get_client, mock_sleep):
    client = fake_client(*[overloaded() for _ in range(MAX_ATTEMPTS)])
    mock_get_client.return_value = client
    with pytest.raises(RuntimeError, match="overloaded"):
        analyze_ingredients("Aqua")
    assert client.chat.completions.create.call_count == MAX_ATTEMPTS


@patch("artifact.analyzer.time.sleep")
@patch("artifact.analyzer.get_client")
def test_extract_ingredients_from_image_returns_clean_text(mock_get_client, mock_sleep):
    mock_get_client.return_value = fake_client(ok("  Aqua, Glycerin \n"))
    assert extract_ingredients_from_image(b"fake image") == "Aqua, Glycerin"


@patch("artifact.analyzer.time.sleep")
@patch("artifact.analyzer.get_client")
def test_extract_ingredients_raises_when_model_keeps_failing(
    mock_get_client, mock_sleep
):
    mock_get_client.return_value = fake_client(
        *[overloaded() for _ in range(MAX_ATTEMPTS)]
    )
    with pytest.raises(RuntimeError):
        extract_ingredients_from_image(b"fake image")
