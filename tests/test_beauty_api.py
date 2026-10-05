from unittest.mock import MagicMock, patch

from artifact.beauty_api import get_product_by_barcode


def fake_response(payload):
    response = MagicMock()
    response.json.return_value = payload
    return response


@patch("artifact.beauty_api.requests.get")
def test_product_found_with_ingredients(mock_get):
    mock_get.return_value = fake_response(
        {
            "status": 1,
            "product": {
                "product_name": "Cream",
                "brands": "Acme",
                "ingredients_text": "Aqua, Glycerin",
            },
        }
    )
    result = get_product_by_barcode("123")
    assert result == {
        "name": "Cream",
        "brand": "Acme",
        "ingredients_text": "Aqua, Glycerin",
    }


@patch("artifact.beauty_api.requests.get")
def test_unknown_barcode_returns_none(mock_get):
    mock_get.return_value = fake_response({"status": 0})
    assert get_product_by_barcode("000") is None


@patch("artifact.beauty_api.requests.get")
def test_missing_name_and_brand_use_defaults(mock_get):
    mock_get.return_value = fake_response(
        {"status": 1, "product": {"ingredients_text": "Aqua"}}
    )
    result = get_product_by_barcode("123")
    assert result is not None
    assert result["name"] == "Unknown Product"
    assert result["brand"] == "Unknown Brand"


@patch("artifact.beauty_api.requests.get")
def test_falls_back_to_language_specific_ingredients(mock_get):
    mock_get.return_value = fake_response(
        {
            "status": 1,
            "product": {
                "product_name": "Crema",
                "ingredients_text": "",
                "ingredients_text_it": "Acqua, Glicerina",
            },
        }
    )
    result = get_product_by_barcode("123")
    assert result is not None
    assert result["ingredients_text"] == "Acqua, Glicerina"


@patch("artifact.beauty_api.requests.get")
def test_product_without_ingredients_returns_empty_text(mock_get):
    mock_get.return_value = fake_response(
        {"status": 1, "product": {"product_name": "Spray", "ingredients_text": "   "}}
    )
    result = get_product_by_barcode("123")
    assert result is not None
    assert result["ingredients_text"] == ""


@patch("artifact.beauty_api.requests.get", side_effect=Exception("network down"))
def test_network_error_returns_none(mock_get):
    assert get_product_by_barcode("123") is None
