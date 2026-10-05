import re

import requests

_LANGUAGE_FIELD = re.compile(r"ingredients_text_[a-z]{2}")


def _extract_ingredients(product: dict) -> str:
    """Return the ingredient list, falling back to any language-specific field."""
    text = product.get("ingredients_text") or ""
    if text.strip():
        return text.strip()
    for key, value in product.items():
        if _LANGUAGE_FIELD.fullmatch(key) and isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def get_product_by_barcode(barcode: str) -> dict | None:
    url = f"https://world.openbeautyfacts.org/api/v0/product/{barcode}.json"

    try:
        response = requests.get(url, timeout=10)
        data = response.json()

        if data.get("status") != 1:
            return None

        product = data["product"]

        return {
            "name": product.get("product_name") or "Unknown Product",
            "brand": product.get("brands") or "Unknown Brand",
            "ingredients_text": _extract_ingredients(product),
        }

    except Exception:
        return None
