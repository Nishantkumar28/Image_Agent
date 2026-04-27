import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    raise ValueError("ANTHROPIC_API_KEY is missing. Please set it in .env file.")

MAX_IMAGE_SIZE_MB = int(os.getenv("MAX_IMAGE_SIZE_MB", 20))

# Convert local relative paths to absolute based on project root if they start with ./
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
raw_out = os.getenv("OUTPUT_DIR", "./outputs")
raw_temp = os.getenv("TEMP_DIR", "./temp")

OUTPUT_DIR = os.path.join(root_dir, raw_out.strip("./")) if raw_out.startswith("./") else raw_out
TEMP_DIR = os.path.join(root_dir, raw_temp.strip("./")) if raw_temp.startswith("./") else raw_temp

# Ensure directories exist
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)
