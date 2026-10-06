import base64
import json
import os
import time
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# Free models are tried in order: when one provider is overloaded we move on to the next.
TEXT_MODELS = [
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "google/gemma-4-31b-it:free",
    "google/gemma-4-26b-a4b-it:free",
]
VISION_MODELS = [
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
    "google/gemma-4-31b-it:free",
    "google/gemma-4-26b-a4b-it:free",
]
REQUEST_TIMEOUT = 120
ATTEMPTS_PER_MODEL = 2
RETRY_DELAY_SECONDS = 2


def get_client() -> OpenAI:
    # max_retries=0: retrying is handled explicitly in _complete()
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("GEMINI_API_KEY"),
        max_retries=0,
    )


def _describe_error(response: Any) -> str:
    """OpenRouter may answer HTTP 200 with an `error` body and no choices."""
    error = getattr(response, "error", None)
    if isinstance(error, dict):
        return str(error.get("message") or error)
    if error:
        return str(error)
    return "empty response"


def _complete(models: list[str], messages: Any) -> str:
    """Ask the models in order, retrying each when the free provider is overloaded or empty."""
    last_error = "empty response"
    for model in models:
        for attempt in range(ATTEMPTS_PER_MODEL):
            response = get_client().chat.completions.create(
                model=model, messages=messages, timeout=REQUEST_TIMEOUT
            )
            content = response.choices[0].message.content if response.choices else None
            if content and content.strip():
                return content
            last_error = f"{model}: {_describe_error(response)}"
            if attempt < ATTEMPTS_PER_MODEL - 1:
                time.sleep(RETRY_DELAY_SECONDS)
    raise RuntimeError(f"No AI model gave a usable answer (last error: {last_error}).")


def _detect_mime_type(image_bytes: bytes) -> str:
    """Read the real image format from the first bytes; default to JPEG."""
    if image_bytes.startswith(b"\x89PNG"):
        return "image/png"
    if image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"


def analyze_ingredients(ingredients_text: str) -> dict:
    prompt = f"""You are a cosmetic safety expert. Analyze the following personal care product ingredient list and return ONLY a JSON object, no explanation, no markdown.

The JSON must have exactly this structure:
{{
  "summary": "2-3 sentence plain language summary of the product safety",
  "flagged": [
    {{
      "name": "ingredient name",
      "reason": "why it is concerning",
      "severity": "high" or "medium" or "low"
    }}
  ],
  "safe_highlights": ["beneficial ingredient 1", "beneficial ingredient 2"],
  "score": a number between 0 and 100
}}

Scoring rules:
- Start at 100
- Subtract 20 for each high severity ingredient
- Subtract 10 for each medium severity ingredient
- Subtract 3 for each low severity ingredient
- Add 2 for each beneficial ingredient
- Minimum score is 0, maximum is 100

Ingredient list:
{ingredients_text}"""

    raw = _complete(TEXT_MODELS, [{"role": "user", "content": prompt}])
    clean = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(clean)


def extract_ingredients_from_image(image_bytes: bytes) -> str:
    b64_image = base64.b64encode(image_bytes).decode("utf-8")
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "This image shows the ingredient list of a personal care product. Return ONLY the ingredient list as plain comma-separated text, with no explanation or extra formatting.",
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{_detect_mime_type(image_bytes)};base64,{b64_image}"
                    },
                },
            ],
        }
    ]
    return _complete(VISION_MODELS, messages).strip()
