from flask import Blueprint, Flask, jsonify, render_template, request

from artifact.analyzer import analyze_ingredients, extract_ingredients_from_image
from artifact.beauty_api import get_product_by_barcode
from artifact.database import (
    find_cached_analysis,
    get_history,
    init_db,
    parse_list,
    save_analysis,
)

app = Flask(__name__, template_folder="../templates")
init_db()
api_v1 = Blueprint("api_v1", __name__, url_prefix="/api/v1")


AI_FAILED = {
    "error": "ai_failed",
    "message": "AI analysis is temporarily unavailable. Please try again in a moment.",
}


def analyze_with_cache(barcode, product_name, brand, ingredients_text):
    """Reuse a saved result for the same ingredients; call the AI only if none."""
    cached = find_cached_analysis(ingredients_text)
    if cached is not None:
        return cached, True
    result = analyze_ingredients(ingredients_text)
    save_analysis(barcode, product_name, brand, ingredients_text, result)
    return result, False


def result_response(product_name, brand, result, cached):
    return jsonify(
        {
            "product_name": product_name,
            "brand": brand,
            "score": result["score"],
            "summary": result["summary"],
            "flagged": result["flagged"],
            "safe_highlights": result["safe_highlights"],
            "cached": cached,
        }
    )


@app.route("/")  # main page
def index():
    return render_template("index.html")


@api_v1.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json()
    barcode = data.get("barcode", "").strip()
    manual_ingredients = data.get("ingredients", "").strip()

    product_name = "Manual Entry"
    brand = "Unknown"
    ingredients_text = manual_ingredients

    if barcode:
        product = get_product_by_barcode(barcode)
        if product and product.get("ingredients_text"):
            ingredients_text = product["ingredients_text"]
            product_name = product["name"]
            brand = product["brand"]
        elif not manual_ingredients:
            return jsonify(
                {
                    "error": "not_found",
                    "message": "Product not found. Please enter the ingredients manually.",
                }
            ), 404

    if not ingredients_text:
        return jsonify({"error": "Please provide a barcode or ingredients"}), 400

    try:
        result, cached = analyze_with_cache(
            barcode, product_name, brand, ingredients_text
        )
    except Exception:
        app.logger.exception("AI call failed")
        return jsonify(AI_FAILED), 503

    return result_response(product_name, brand, result, cached)


@api_v1.route("/analyze-photo", methods=["POST"])
def analyze_photo():
    photo = request.files.get("photo")
    if not photo:
        return jsonify({"error": "No photo provided"}), 400

    image_bytes = photo.read()

    try:
        ingredients_text = extract_ingredients_from_image(image_bytes)
    except Exception:
        app.logger.exception("AI call failed")
        return jsonify(AI_FAILED), 503

    if not ingredients_text:
        return jsonify({"error": "Could not read ingredients from photo"}), 422

    try:
        result, cached = analyze_with_cache(
            None, "Photo Entry", "Unknown", ingredients_text
        )
    except Exception:
        app.logger.exception("AI call failed")
        return jsonify(AI_FAILED), 503

    return result_response("Photo Entry", "Unknown", result, cached)


def input_method(analysis):
    if analysis.barcode:
        return "barcode"
    if analysis.product_name == "Photo Entry":
        return "photo"
    return "manual"


def safe_list(text):
    try:
        return parse_list(text)
    except (TypeError, ValueError, SyntaxError):
        return []


@api_v1.route("/history", methods=["GET"])
def history():
    analyses = get_history()
    return jsonify(
        [
            {
                "id": a.id,
                "method": input_method(a),
                "barcode": a.barcode,
                "product_name": a.product_name,
                "brand": a.brand,
                "ingredients_preview": (a.ingredients_text or "")[:60],
                "score": a.score,
                "summary": a.summary,
                "flagged": safe_list(a.flagged_json),
                "safe_highlights": safe_list(a.safe_highlights_json),
                "created_at": a.created_at.isoformat(),
            }
            for a in analyses
        ]
    )


app.register_blueprint(
    api_v1
)  # this one has to comes after all routes toavoid Flask error
