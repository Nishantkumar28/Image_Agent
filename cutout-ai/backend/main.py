import os
import sys
import json
import uuid
import zipfile
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
import aiofiles

# Ensure backend dir is in path when running from backend/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.orchestrator import Orchestrator
from config import OUTPUT_DIR, TEMP_DIR, MAX_IMAGE_SIZE_MB

app = FastAPI(title="CutoutAI", version="1.0")

# CORS - allow all origins (local tool)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount outputs and frontend static directories
app.mount("/files", StaticFiles(directory=OUTPUT_DIR), name="files")

frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

orchestrator = Orchestrator()


@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    index_path = os.path.join(frontend_dir, "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        return f.read()


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0"}


@app.post("/process/url")
async def process_url(request: Request):
    body = await request.json()
    url = body.get("url", "").strip()
    prompt = body.get("prompt", "").strip() or None
    
    if not url:
        raise HTTPException(status_code=400, detail="URL must not be empty.")
    result = orchestrator.run(url, prompt=prompt)
    return JSONResponse(content=result)


@app.post("/process/upload")
async def process_upload(file: UploadFile = File(...), prompt: str = Form(None)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are accepted.")

    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_IMAGE_SIZE_MB:
        raise HTTPException(status_code=413, detail=f"File exceeds {MAX_IMAGE_SIZE_MB}MB limit.")

    ext = os.path.splitext(file.filename or "")[-1] or ".jpg"
    save_path = os.path.join(TEMP_DIR, f"{uuid.uuid4()}_upload{ext}")
    async with aiofiles.open(save_path, "wb") as f:
        await f.write(content)

    result = orchestrator.run(save_path, prompt=prompt)
    return JSONResponse(content=result)


@app.get("/download/{job_id}")
async def download_zip(job_id: str):
    job_dir = os.path.join(OUTPUT_DIR, job_id)
    if not os.path.isdir(job_dir):
        raise HTTPException(status_code=404, detail="Job not found.")

    pngs = list(Path(job_dir).glob("*.png"))
    if not pngs:
        raise HTTPException(status_code=404, detail="No PNG cutouts found for this job.")

    zip_path = os.path.join(job_dir, "cutouts.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for png in pngs:
            zf.write(png, png.name)

    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=f"cutouts_{job_id}.zip",
    )


@app.get("/status/{job_id}")
async def get_status(job_id: str):
    result_path = os.path.join(OUTPUT_DIR, job_id, "result.json")
    if not os.path.exists(result_path):
        return JSONResponse(content={"status": "not_found"})
    with open(result_path, "r") as f:
        return JSONResponse(content=json.load(f))
