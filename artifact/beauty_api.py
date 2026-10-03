import requests


def get_product_by_barcode(barcode: str) -> dict | None:
    url = f"https://world.openbeautyfacts.org/api/v0/product/{barcode}.json"

    try:
        response = requests.get(url, timeout=10)
        data = response.json()

        if data.get("status") != 1:
            return None

        product = data["product"]

        return {
            "name": product.get("product_name", "Unknown Product"),
            "brand": product.get("brands", "Unknown Brand"),
            "ingredients_text": product.get("ingredients_text", ""),
        }

    except Exception:
        return None
