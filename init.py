import os

target = r"c:\ACADAMICS\agent\Image_Agent\cutout-ai"

dirs = [
    "backend/agents",
    "frontend",
    "outputs",
    "temp",
]

for d in dirs:
    os.makedirs(os.path.join(target, d), exist_ok=True)

files = [
    "backend/main.py",
    "backend/tasks.py",
    "backend/storage.py",
    "backend/agents/__init__.py",
    "backend/agents/orchestrator.py",
    "backend/agents/fetcher.py",
    "backend/agents/analyser.py",
    "backend/agents/segmentor.py",
    "backend/agents/enhancer.py",
    "frontend/index.html",
    "frontend/style.css",
    "frontend/app.js",
]

for f in files:
    with open(os.path.join(target, f), "w") as fp:
        pass
