import os
import sys
import base64
import json
import re
from io import BytesIO

from PIL import Image

# Ensure backend imports work when run standalone
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(backend_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.config import ANTHROPIC_API_KEY, TEMP_DIR
import anthropic

SYSTEM_PROMPT = """You are an image analysis expert for a video editing tool. 
Your job is to identify every distinct character, person, animal, 
or significant object in an image that could be extracted as a 
cutout for use in video production. 

Rules:
- Only list objects that have clear, identifiable boundaries
- Do not list backgrounds, skies, floors, walls, or gradients
- Do not list shadows as separate objects
- Each object must be meaningfully distinct from others
- Estimate the center point as a percentage of image width/height
- Confidence score: 0.0 to 1.0 based on how clear the boundaries are

Return ONLY valid JSON. No explanation. No markdown. No backticks.
Format exactly:
{
  "objects": [
    {
      "id": 1,
      "label": "woman in red dress",
      "center_x_pct": 0.35,
      "center_y_pct": 0.50,
      "estimated_size": "large",
      "confidence": 0.95
    }
  ]
}"""


class SceneAnalyser:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    def _prepare_image(self, image_path: str) -> tuple[str, str]:
        """Resize if needed, return base64 string and media type."""
        img = Image.open(image_path)
        
        max_side = 1568
        w, h = img.size
        if w > max_side or h > max_side:
            ratio = min(max_side / w, max_side / h)
            new_w = int(w * ratio)
            new_h = int(h * ratio)
            img = img.resize((new_w, new_h), Image.LANCZOS)

        # Convert to RGB for JPEG encoding if RGBA
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=90)
        buffer.seek(0)
        img_b64 = base64.b64encode(buffer.read()).decode("utf-8")
        return img_b64, "image/jpeg"

    def _call_claude(self, img_b64: str, media_type: str, retry: bool = False) -> str:
        user_msg = "Analyse this image and return the JSON list of objects." 
        if retry:
            user_msg += " IMPORTANT: Return ONLY raw JSON with no explanation, no markdown, no backticks."
        
        message = self.client.messages.create(
            model="claude-opus-4-5",
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": img_b64,
                            },
                        },
                        {"type": "text", "text": user_msg},
                    ],
                }
            ],
        )
        return message.content[0].text

    def _parse_response(self, raw: str) -> list[dict]:
        # Strip markdown fences if present
        text = raw.strip()
        text = re.sub(r"^```[a-z]*\n?", "", text)
        text = re.sub(r"```$", "", text)
        text = text.strip()
        data = json.loads(text)
        return data.get("objects", [])

    def analyse(self, image_path: str) -> list[dict]:
        img_b64, media_type = self._prepare_image(image_path)

        try:
            raw = self._call_claude(img_b64, media_type, retry=False)
            objects = self._parse_response(raw)
        except (json.JSONDecodeError, KeyError, ValueError):
            # Retry once
            try:
                raw = self._call_claude(img_b64, media_type, retry=True)
                objects = self._parse_response(raw)
            except Exception as e:
                raise ValueError(f"Failed to parse Claude response after retry. Raw: {raw}") from e

        # Filter low-confidence objects
        objects = [obj for obj in objects if obj.get("confidence", 0) >= 0.5]
        return objects


if __name__ == "__main__":
    import requests
    import uuid

    test_url = "https://picsum.photos/800/600"
    test_path = os.path.join(TEMP_DIR, f"{uuid.uuid4()}_analyser_test.jpg")
    resp = requests.get(test_url, timeout=10)
    with open(test_path, "wb") as f:
        f.write(resp.content)

    analyser = SceneAnalyser()
    try:
        objects = analyser.analyse(test_path)
        print("Objects found:")
        for obj in objects:
            print(f"  - {obj}")
        print("PHASE 3 COMPLETE")
    except Exception as e:
        print(f"PHASE 3 FAILED: {e}")
