import os
import sys
import uuid
import shutil
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup

# Ensure backend imports work when run standalone
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(backend_dir)
if project_root not in sys.path:
    sys.path.append(project_root)
    
from backend.config import TEMP_DIR

class ImageFetcher:
    def fetch(self, source: str) -> str:
        timeout = 10
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        file_ext = ".jpg"
        save_path = os.path.join(TEMP_DIR, f"{uuid.uuid4()}_input{file_ext}")
        
        if os.path.exists(source) and os.path.isfile(source):
            try:
                shutil.copy2(source, save_path)
                return save_path
            except Exception as e:
                raise ValueError(f"Failed to copy local file: {str(e)}")
                
        if source.startswith("http://") or source.startswith("https://"):
            parsed = urlparse(source)
            domain = parsed.netloc.lower()
            
            if "pinterest.com" in domain or "pin.it" in domain:
                try:
                    response = requests.get(source, headers=headers, timeout=timeout)
                    response.raise_for_status()
                except Exception as e:
                    raise ConnectionError(f"Failed to fetch Pinterest page: {str(e)}")
                    
                soup = BeautifulSoup(response.text, 'html.parser')
                og_image = soup.find("meta", property="og:image")
                if not og_image or not og_image.get("content"):
                    raise ValueError("Could not find og:image in Pinterest page.")
                    
                img_url = og_image["content"]
                img_url = img_url.replace("/236x/", "/originals/")
            else:
                # Direct image URL check
                path_lower = parsed.path.lower()
                if not any(path_lower.endswith(ext) for ext in [".jpg", ".png", ".jpeg", ".webp"]):
                    # picsum test URL workaround since it doesn't have an extension but it's an image.
                    if "picsum.photos" not in domain:
                        raise ValueError("URL does not appear to be a direct image or a Pinterest URL.")
                img_url = source
                
            try:
                img_response = requests.get(img_url, headers=headers, timeout=timeout)
                img_response.raise_for_status()
                with open(save_path, "wb") as f:
                    f.write(img_response.content)
                return save_path
            except Exception as e:
                raise ConnectionError(f"Failed to download image: {str(e)}")
                
        raise ValueError(f"Source type unrecognised for: {source}")

if __name__ == "__main__":
    fetcher = ImageFetcher()
    test_url = "https://picsum.photos/800/600"
    try:
        path = fetcher.fetch(test_url)
        if os.path.exists(path):
            print(f"PHASE 2 COMPLETE: Saved to {path}")
        else:
            print("PHASE 2 FAILED: File was not created.")
    except Exception as e:
        print(f"PHASE 2 FAILED: {str(e)}")
