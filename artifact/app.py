from flask import Blueprint, Flask, render_template, request, jsonify
from artifact.database import init_db, save_analysis, get_history
from artifact.beauty_api import get_product_by_barcode
from artifact.analyzer import analyze_ingredients, extract_ingredients_from_image

app = Flask(__name__, template_folder="../templates")
init_db()
api_v1 = Blueprint("api_v1", __name__, url_prefix="/api/v1")


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
        result = analyze_ingredients(ingredients_text)
    except Exception:
        app.logger.exception("AI call failed")
        return jsonify(
            {
                "error": "ai_failed",
                "message": "AI analysis is temporarily unavailable. Please try again in a moment.",
            }
        ), 503

    save_analysis(barcode, product_name, brand, ingredients_text, result)

    return jsonify(
        {
            "product_name": product_name,
            "brand": brand,
            "score": result["score"],
            "summary": result["summary"],
            "flagged": result["flagged"],
            "safe_highlights": result["safe_highlights"],
        }
    )


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
        return jsonify(
            {
                "error": "ai_failed",
                "message": "AI analysis is temporarily unavailable. Please try again in a moment.",
            }
        ), 503

    if not ingredients_text:
        return jsonify({"error": "Could not read ingredients from photo"}), 422

    try:
        result = analyze_ingredients(ingredients_text)
    except Exception:
        app.logger.exception("AI call failed")
        return jsonify(
            {
                "error": "ai_failed",
                "message": "AI analysis is temporarily unavailable. Please try again in a moment.",
            }
        ), 503

    save_analysis(None, "Photo Entry", "Unknown", ingredients_text, result)

    return jsonify(
        {
            "product_name": "Photo Entry",
            "brand": "Unknown",
            "score": result["score"],
            "summary": result["summary"],
            "flagged": result["flagged"],
            "safe_highlights": result["safe_highlights"],
        }
    )


@api_v1.route("/history", methods=["GET"])
def history():
    analyses = get_history()
    return jsonify(
        [
            {
                "id": a.id,
                "barcode": a.barcode,
                "product_name": a.product_name,
                "brand": a.brand,
                "score": a.score,
                "summary": a.summary,
                "created_at": a.created_at.isoformat(),
            }
            for a in analyses
        ]
    )


app.register_blueprint(
    api_v1
)  # this one has to comes after all routes toavoid Flask error
