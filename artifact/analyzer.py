import os
import json
import base64
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


def get_client() -> OpenAI:
    return OpenAI(
        base_url="https://openrouter.ai/api/v1", api_key=os.getenv("GEMINI_API_KEY")
    )


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

    response = get_client().chat.completions.create(
        model="nvidia/nemotron-3-ultra-550b-a55b:free",
        messages=[{"role": "user", "content": prompt}],
        timeout=120,
    )

    if not response.choices or response.choices[0].message.content is None:
        raise RuntimeError("AI model returned an empty response. Please try again.")

    raw = response.choices[0].message.content
    clean = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(clean)


def extract_ingredients_from_image(image_bytes: bytes) -> str:
    b64_image = base64.b64encode(image_bytes).decode("utf-8")

    response = get_client().chat.completions.create(
        model="nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "This image shows the ingredient list of a personal care product. Return ONLY the ingredient list as plain comma-separated text, with no explanation or extra formatting.",
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"},
                    },
                ],
            }
        ],
        timeout=120,
    )

    if not response.choices or response.choices[0].message.content is None:
        raise RuntimeError("AI model returned an empty response. Please try again.")

    return response.choices[0].message.content.strip()
