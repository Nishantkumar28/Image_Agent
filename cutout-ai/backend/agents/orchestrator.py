import os
import sys
import uuid
import json
import logging
from pathlib import Path

# Ensure backend imports work when run standalone
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(backend_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.agents.fetcher import ImageFetcher
from backend.agents.analyser import SceneAnalyser
from backend.agents.segmentor import Segmentor
from backend.agents.enhancer import Enhancer
from backend.config import OUTPUT_DIR

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class Orchestrator:
    def __init__(self):
        self.fetcher = ImageFetcher()
        self.analyser = SceneAnalyser()
        self.segmentor = Segmentor()
        self.enhancer = Enhancer()

    def run(self, source: str, prompt: str = None) -> dict:
        job_id = str(uuid.uuid4())[:8]
        result = {
            "job_id": job_id,
            "source": source,
            "status": "started",
            "steps": [],
            "cutouts": [],
            "error": None,
        }

        # STEP 1 — Fetch image
        try:
            image_path = self.fetcher.fetch(source)
            result["steps"].append({"step": "fetch", "status": "ok", "file": image_path})
            logger.info(f"[{job_id}] Fetched: {image_path}")
        except Exception as e:
            result["status"] = "failed"
            result["error"] = f"Fetch failed: {str(e)}"
            return result

        # STEP 2 — Analyse scene
        try:
            objects = self.analyser.analyse(image_path, prompt=prompt)
            result["steps"].append({"step": "analyse", "status": "ok", "objects_found": len(objects)})
            logger.info(f"[{job_id}] Found {len(objects)} objects.")
        except Exception as e:
            result["status"] = "failed"
            result["error"] = f"Analyse failed: {str(e)}"
            return result

        if not objects:
            result["status"] = "completed"
            result["message"] = "No cuttable objects found in this image."
            result["cutouts"] = []
            result["total_cutouts"] = 0
            return result

        # STEP 3 — Segment objects
        try:
            cutout_files = self.segmentor.segment(image_path, objects, job_id)
            result["steps"].append({"step": "segment", "status": "ok", "cutouts_created": len(cutout_files)})
            logger.info(f"[{job_id}] Created {len(cutout_files)} cutouts.")
        except Exception as e:
            result["status"] = "failed"
            result["error"] = f"Segment failed: {str(e)}"
            return result

        # STEP 4 — Enhance cutouts
        try:
            self.enhancer.enhance_all([c["file_path"] for c in cutout_files])
            result["steps"].append({"step": "enhance", "status": "ok"})
            logger.info(f"[{job_id}] Enhanced all cutouts.")
        except Exception as e:
            logger.warning(f"[{job_id}] Enhance step issue (non-fatal): {e}")
            result["steps"].append({"step": "enhance", "status": "warning", "detail": str(e)})

        # STEP 5 — Finalise
        result["status"] = "completed"
        result["cutouts"] = cutout_files
        result["total_cutouts"] = len(cutout_files)

        # Save result JSON
        job_dir = os.path.join(OUTPUT_DIR, job_id)
        os.makedirs(job_dir, exist_ok=True)
        result_path = os.path.join(job_dir, "result.json")
        with open(result_path, "w") as f:
            json.dump(result, f, indent=2)
        logger.info(f"[{job_id}] Result saved to {result_path}")

        return result


if __name__ == "__main__":
    orch = Orchestrator()
    test_url = "https://picsum.photos/1200/800"
    print(f"Running full pipeline on: {test_url}")
    result = orch.run(test_url)
    print(json.dumps(result, indent=2))
    if result["status"] == "completed":
        print("PHASE 6 COMPLETE")
    else:
        print(f"PHASE 6 FAILED: {result.get('error')}")
