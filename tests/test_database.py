from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from artifact import database
from artifact.database import (
    Analysis,
    Base,
    find_cached_analysis,
    normalize_ingredients,
    parse_list,
    save_analysis,
)

RESULT = {
    "score": 61,
    "summary": "Some fragrance allergens.",
    "flagged": [{"name": "Parfum", "reason": "Allergen", "severity": "medium"}],
    "safe_highlights": ["Glycerin"],
}


@pytest.fixture(autouse=True)
def test_db():
    """Use a fresh in-memory database instead of realbeauty.db."""
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)
    with patch.object(database, "Session", TestSession):
        yield TestSession


def test_normalize_removes_extra_spaces():
    assert normalize_ingredients("  Aqua,\n  Glycerin ") == "Aqua, Glycerin"


def test_find_cached_returns_none_when_not_saved():
    assert find_cached_analysis("Aqua, Glycerin") is None


def test_find_cached_ignores_case_and_spaces():
    save_analysis(None, "Manual Entry", "Unknown", "Aqua, Glycerin", RESULT)
    cached = find_cached_analysis("aqua,   GLYCERIN")
    assert cached == RESULT


def test_find_cached_reads_rows_in_old_format(test_db):
    session = test_db()
    session.add(
        Analysis(
            product_name="Manual Entry",
            brand="Unknown",
            ingredients_text="Aqua, Parabens",
            score=35,
            summary="Concerning.",
            flagged_json=str(RESULT["flagged"]),  # old format: single quotes
            safe_highlights_json=str(RESULT["safe_highlights"]),
        )
    )
    session.commit()
    session.close()
    assert find_cached_analysis("aqua, parabens")["flagged"][0]["name"] == "Parfum"


def test_parse_list_reads_json_and_old_format():
    assert parse_list('["Glycerin"]') == ["Glycerin"]
    assert parse_list("['Glycerin']") == ["Glycerin"]
