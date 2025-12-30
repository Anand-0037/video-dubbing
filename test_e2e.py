
import requests
import time
import os
import sys

API_URL = "http://localhost:8000/api/v1"
VIDEO_PATH = "test_video.mp4"

def test_flow():
    if not os.path.exists(VIDEO_PATH):
        print(f"Video file not found: {VIDEO_PATH}")
        return

    # 1. Create Job
    print("Creating Job...")
    try:
        resp = requests.post(f"{API_URL}/jobs", json={
            "source_language": "english",
            "target_language": "hindi",
            "voice_id": "pNInz6obpgDQGcFmaJgB",
            "filename": "test_video.mp4",
            "content_type": "video/mp4",
            "file_size": os.path.getsize(VIDEO_PATH)
        })
        resp.raise_for_status()
        data = resp.json()["data"]
        job_id = data["job_id"]
        upload_url = data["upload_url"]
        print(f"Job Created: {job_id}")
        print(f"Upload URL: {upload_url[:50]}...")
    except Exception as e:
        print(f"Create Job Failed: {e}")
        if 'resp' in locals(): print(resp.text)
        return

    # 2. Upload Video
    print("Uploading Video...")
    try:
        with open(VIDEO_PATH, "rb") as f:
            upload_resp = requests.put(upload_url, data=f, headers={"Content-Type": "video/mp4"})
            upload_resp.raise_for_status()
        print("Upload Successful")
    except Exception as e:
        print(f"Upload Failed: {e}")
        if 'upload_resp' in locals(): print(upload_resp.text)
        return

    # 3. Enqueue Job
    print("Enqueuing Job...")
    try:
        resp = requests.post(f"{API_URL}/jobs/{job_id}/enqueue")
        resp.raise_for_status()
        print("Job Enqueued")
    except Exception as e:
        print(f"Enqueue Failed: {e}")
        if 'resp' in locals(): print(resp.text)
        return

    # 4. Poll Status
    print("Polling Status...")
    start_time = time.time()
    while time.time() - start_time < 300: # 5 mins timeout
        try:
            resp = requests.get(f"{API_URL}/jobs/{job_id}")
            resp.raise_for_status()
            data = resp.json()["data"]
            status = data["status"]
            progress = data.get("progress", 0)
            print(f"Status: {status} ({progress}%)")

            if status == "done":
                print("Job Completed Successfully!")
                return
            if status == "failed":
                error = resp.json().get("error_message", "Unknown error")
                print(f"Job Failed: {error}")
                return

            time.sleep(5)
        except Exception as e:
            print(f"Polling Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    test_flow()
