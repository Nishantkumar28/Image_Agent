import os
import sys
import logging

from PIL import Image, ImageFilter, ImageEnhance

# Ensure backend imports work when run standalone
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(backend_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class Enhancer:
    def enhance(self, image_path: str) -> str:
        img = Image.open(image_path).convert("RGBA")

        # STEP A — Upscale if needed
        w, h = img.size
        if w < 800 or h < 800:
            img = img.resize((w * 2, h * 2), Image.LANCZOS)

        # STEP B — Sharpen RGB only (preserve alpha)
        r, g, b, a = img.split()
        rgb = Image.merge("RGB", (r, g, b))
        rgb = rgb.filter(ImageFilter.SHARPEN)
        r2, g2, b2 = rgb.split()
        img = Image.merge("RGBA", (r2, g2, b2, a))

        # STEP C — Smooth alpha channel only
        r3, g3, b3, a3 = img.split()
        a3_smooth = a3.filter(ImageFilter.GaussianBlur(radius=0.5))
        img = Image.merge("RGBA", (r3, g3, b3, a3_smooth))

        # STEP D — Contrast boost on RGB only
        r4, g4, b4, a4 = img.split()
        rgb2 = Image.merge("RGB", (r4, g4, b4))
        rgb2 = ImageEnhance.Contrast(rgb2).enhance(1.1)
        r5, g5, b5 = rgb2.split()
        img = Image.merge("RGBA", (r5, g5, b5, a4))

        # STEP E — Save
        img.save(image_path, "PNG", optimize=True)
        logger.info(f"Enhanced: {image_path}")
        return image_path

    def enhance_all(self, file_paths: list) -> list:
        results = []
        for path in file_paths:
            try:
                enhanced = self.enhance(path)
                results.append(enhanced)
            except Exception as e:
                logger.error(f"Failed to enhance {path}: {e}")
        return results


if __name__ == "__main__":
    import glob

    # Find any PNG in outputs/
    outputs_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "outputs",
    )
    pngs = glob.glob(os.path.join(outputs_dir, "**", "*.png"), recursive=True)

    if not pngs:
        print("PHASE 5 FAILED: No PNG found in outputs/ to test enhancer. Run Phase 4 first.")
        sys.exit(1)

    enhancer = Enhancer()
    test_file = pngs[0]
    try:
        result = enhancer.enhance(test_file)
        print(f"Enhanced: {result}")
        print("PHASE 5 COMPLETE")
    except Exception as e:
        print(f"PHASE 5 FAILED: {e}")
