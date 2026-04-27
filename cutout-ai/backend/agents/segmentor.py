import os
import sys
import io
import logging

from PIL import Image
from rembg import remove

# Ensure backend imports work when run standalone
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(backend_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.config import OUTPUT_DIR

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def _label_to_snake(label: str) -> str:
    """Convert a label to a snake_case filename-safe string."""
    import re
    s = label.lower().strip()
    s = re.sub(r'[^a-z0-9]+', '_', s)
    s = s.strip('_')
    return s[:60]  # limit length


def _auto_trim_transparent(img: Image.Image, padding: int = 15) -> Image.Image:
    """Remove fully transparent rows/columns from edges then add padding."""
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    
    data = img.load()
    w, h = img.size

    # Find bounding box of non-transparent pixels
    left, top, right, bottom = w, h, 0, 0
    for y in range(h):
        for x in range(w):
            if data[x, y][3] > 0:
                left = min(left, x)
                top = min(top, y)
                right = max(right, x)
                bottom = max(bottom, y)

    if right < left or bottom < top:
        return img  # fully transparent, return as-is

    cropped = img.crop((left, top, right + 1, bottom + 1))
    cw, ch = cropped.size
    padded = Image.new("RGBA", (cw + padding * 2, ch + padding * 2), (0, 0, 0, 0))
    padded.paste(cropped, (padding, padding))
    return padded


class Segmentor:
    def segment(self, image_path: str, objects: list[dict], job_id: str) -> list[dict]:
        job_output_dir = os.path.join(OUTPUT_DIR, job_id)
        os.makedirs(job_output_dir, exist_ok=True)

        # Run rembg once for the full image
        with open(image_path, "rb") as f:
            input_data = f.read()
        output_data = remove(input_data)
        full_removed = Image.open(io.BytesIO(output_data)).convert("RGBA")
        img_w, img_h = full_removed.size

        results = []
        size_map = {"large": 0.70, "medium": 0.45, "small": 0.25}

        for obj in objects:
            try:
                label = obj.get("label", f"object_{obj.get('id', 0)}")
                cx_pct = obj.get("center_x_pct", 0.5)
                cy_pct = obj.get("center_y_pct", 0.5)
                size_key = obj.get("estimated_size", "medium")
                factor = size_map.get(size_key, 0.45)

                cx = int(cx_pct * img_w)
                cy = int(cy_pct * img_h)

                half_w = int((factor * img_w) / 2)
                half_h = int((factor * img_h) / 2)

                x1 = max(0, cx - half_w)
                y1 = max(0, cy - half_h)
                x2 = min(img_w, cx + half_w)
                y2 = min(img_h, cy + half_h)

                cropped = full_removed.crop((x1, y1, x2, y2))
                cleaned = _auto_trim_transparent(cropped, padding=15)

                filename = f"{_label_to_snake(label)}.png"
                save_path = os.path.join(job_output_dir, filename)
                cleaned.save(save_path, "PNG", optimize=True)

                results.append({
                    "label": label,
                    "file_path": save_path,
                    "confidence": obj.get("confidence", 1.0),
                })
                logger.info(f"Segmented: {label} -> {save_path}")

            except Exception as e:
                logger.error(f"Failed to segment object '{obj.get('label', '?')}': {e}")
                continue

        return results


if __name__ == "__main__":
    import requests
    import uuid as uuid_mod

    # Download test image
    test_url = "https://picsum.photos/800/600"
    test_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "temp",
        f"{uuid_mod.uuid4()}_seg_test.jpg",
    )
    resp = requests.get(test_url, timeout=10)
    with open(test_path, "wb") as f:
        f.write(resp.content)

    mock_objects = [
        {
            "id": 1,
            "label": "landscape scene",
            "center_x_pct": 0.5,
            "center_y_pct": 0.5,
            "estimated_size": "large",
            "confidence": 0.9,
        }
    ]

    seg = Segmentor()
    job_id = f"test_{uuid_mod.uuid4().hex[:6]}"
    try:
        results = seg.segment(test_path, mock_objects, job_id)
        for r in results:
            print(f"  Saved: {r['file_path']}")
        print("PHASE 4 COMPLETE")
    except Exception as e:
        print(f"PHASE 4 FAILED: {e}")
