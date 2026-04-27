import requests
import time
import os
import sys

BASE_URL = "http://localhost:8000"

def run_tests():
    print("Starting Phase 9 Integration Tests...")
    
    # Wait for server to be healthy
    for _ in range(10):
        try:
            res = requests.get(f"{BASE_URL}/health")
            if res.status_code == 200:
                print("Server is up!")
                break
        except requests.ConnectionError:
            time.sleep(1)
    else:
        print("Server not responding")
        sys.exit(1)

    print("\n--- TEST 1: URL Input ---")
    url = "https://picsum.photos/id/237/1200/800" # Using a specific image (dog) to ensure there's an object
    print(f"Sending URL: {url}")
    try:
        r = requests.post(f"{BASE_URL}/process/url", json={"url": url}, timeout=150)
        r.raise_for_status()
        data1 = r.json()
        if data1.get("status") == "completed" and len(data1.get("cutouts", [])) > 0:
            print("TEST 1 PASSED: Got cutouts:", data1["cutouts"])
        else:
            print("TEST 1 FAILED:", data1)
            sys.exit(1)
    except Exception as e:
        print("TEST 1 FAILED Exception:", e)
        sys.exit(1)

    print("\n--- TEST 2: File Upload ---")
    # download an image to upload
    test_img = "test_upload.jpg"
    img_data = requests.get(url).content
    with open(test_img, "wb") as f:
        f.write(img_data)
        
    try:
        with open(test_img, "rb") as f:
            files = {"file": ("test_upload.jpg", f, "image/jpeg")}
            r = requests.post(f"{BASE_URL}/process/upload", files=files, timeout=150)
            r.raise_for_status()
            data2 = r.json()
            if data2.get("status") == "completed" and len(data2.get("cutouts", [])) > 0:
                print("TEST 2 PASSED: Got cutouts for upload")
                job_id = data2["job_id"]
            else:
                print("TEST 2 FAILED:", data2)
                sys.exit(1)
    except Exception as e:
        print("TEST 2 FAILED Exception:", e)
        sys.exit(1)

    print("\n--- TEST 3: ZIP Download ---")
    try:
        r = requests.get(f"{BASE_URL}/download/{job_id}")
        r.raise_for_status()
        content_type = r.headers.get("Content-Type", "")
        if "zip" in content_type.lower() and len(r.content) > 1000:
            print("TEST 3 PASSED: ZIP downloaded successfully, size:", len(r.content))
        else:
            print("TEST 3 FAILED: Invalid zip file received")
            sys.exit(1)
    except Exception as e:
        print("TEST 3 FAILED Exception:", e)
        sys.exit(1)

    print("\nFINAL INTEGRATION TEST PASSED — CutoutAI IS READY.")

if __name__ == "__main__":
    run_tests()
