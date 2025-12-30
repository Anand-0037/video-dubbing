
import os
import shutil
from fastapi import APIRouter, File, UploadFile, Request, HTTPException
from fastapi.responses import FileResponse
from dubwizard_shared.config import shared_settings

router = APIRouter()

UPLOAD_DIR = "/tmp/dubwizard_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.put("/upload/{file_path:path}")
async def upload_file(file_path: str, request: Request):
    """
    Simulate S3 PUT upload.
    Accepts raw body as file content.
    """
    full_path = os.path.join(UPLOAD_DIR, file_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    # Write request body to file
    with open(full_path, "wb") as f:
        async for chunk in request.stream():
            f.write(chunk)

    return {"status": "ok", "path": full_path}

@router.get("/download/{file_path:path}")
async def download_file(file_path: str):
    """Simulate S3 GET download."""
    full_path = os.path.join(UPLOAD_DIR, file_path)
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(full_path)
