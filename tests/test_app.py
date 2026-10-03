from datetime import datetime
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

from artifact.app import app

FAKE_RESULT = {
    "score": 80,
    "summary": "Mostly safe.",
    "flagged": [],
    "safe_highlights": ["Glycerin"],
}


def make_client():
    app.config["TESTING"] = True
    return app.test_client()


def test_index_returns_page():
    response = make_client().get("/")
    assert response.status_code == 200


def test_analyze_without_input_returns_400():
    response = make_client().post("/api/v1/analyze", json={})
    assert response.status_code == 400


@patch("artifact.app.save_analysis")
@patch("artifact.app.analyze_ingredients", return_value=FAKE_RESULT)
def test_analyze_manual_ingredients(mock_analyze, mock_save):
    response = make_client().post(
        "/api/v1/analyze", json={"ingredients": "Aqua, Glycerin"}
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["score"] == 80
    assert data["product_name"] == "Manual Entry"
    mock_save.assert_called_once()


@patch("artifact.app.save_analysis")
@patch("artifact.app.analyze_ingredients", return_value=FAKE_RESULT)
@patch(
    "artifact.app.get_product_by_barcode",
    return_value={
        "name": "Soap",
        "brand": "Acme",
        "ingredients_text": "Aqua, Glycerin",
    },
)
def test_analyze_barcode_found(mock_product, mock_analyze, mock_save):
    response = make_client().post("/api/v1/analyze", json={"barcode": "123"})
    assert response.status_code == 200
    data = response.get_json()
    assert data["product_name"] == "Soap"
    assert data["brand"] == "Acme"


@patch("artifact.app.get_product_by_barcode", return_value=None)
def test_analyze_barcode_not_found_returns_404(mock_product):
    response = make_client().post("/api/v1/analyze", json={"barcode": "000"})
    assert response.status_code == 404
    assert response.get_json()["error"] == "not_found"


@patch("artifact.app.analyze_ingredients", side_effect=RuntimeError("boom"))
def test_analyze_ai_failure_returns_503(mock_analyze):
    response = make_client().post("/api/v1/analyze", json={"ingredients": "Aqua"})
    assert response.status_code == 503
    assert response.get_json()["error"] == "ai_failed"


def test_analyze_photo_without_file_returns_400():
    response = make_client().post("/api/v1/analyze-photo")
    assert response.status_code == 400


@patch("artifact.app.save_analysis")
@patch("artifact.app.analyze_ingredients", return_value=FAKE_RESULT)
@patch("artifact.app.extract_ingredients_from_image", return_value="Aqua, Glycerin")
def test_analyze_photo_success(mock_extract, mock_analyze, mock_save):
    response = make_client().post(
        "/api/v1/analyze-photo",
        data={"photo": (BytesIO(b"fake image"), "label.jpg")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    assert response.get_json()["product_name"] == "Photo Entry"


@patch("artifact.app.extract_ingredients_from_image", return_value="")
def test_analyze_photo_unreadable_returns_422(mock_extract):
    response = make_client().post(
        "/api/v1/analyze-photo",
        data={"photo": (BytesIO(b"fake image"), "label.jpg")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 422


@patch("artifact.app.get_history")
def test_history_returns_saved_analyses(mock_history):
    mock_history.return_value = [
        SimpleNamespace(
            id=1,
            barcode="123",
            product_name="Soap",
            brand="Acme",
            score=80,
            summary="Mostly safe.",
            created_at=datetime(2026, 10, 3),
        )
    ]
    response = make_client().get("/api/v1/history")
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 1
    assert data[0]["product_name"] == "Soap"
