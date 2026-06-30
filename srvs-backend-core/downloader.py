import sys
import subprocess
import re
import os
from fastapi import HTTPException

# Package presence validation & runtime installation
try:
    import gdown
except ImportError:
    print("[SYSTEM] 'gdown' package not found. Initiating pip installation...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "gdown"], check=True)
        import gdown
    except Exception as install_err:
        raise RuntimeError(f"Failed to auto-install gdown: {install_err}")

def download_drive_file(file_id: str) -> str:
    # Strict validation guard to prevent command injection/path traversal
    if not re.match(r"^[a-zA-Z0-9-_]+$", file_id):
        raise HTTPException(status_code=400, detail="Invalid File ID format")
    
    # Resolve absolute path to the data/videos folder in the core directory
    base_dir = os.path.dirname(os.path.abspath(__file__))
    videos_dir = os.path.join(base_dir, "data", "videos")
    os.makedirs(videos_dir, exist_ok=True)
    
    output_path = os.path.join(videos_dir, f"{file_id}.mp4")
    url = f"https://drive.google.com/uc?id={file_id}"
    
    # If the file already exists, return it directly to avoid duplicate downloads
    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
        print(f"[SYSTEM] File {file_id}.mp4 already exists locally. Skipping download.")
        return output_path

    try:
        print(f"[SYSTEM] Initiating gdown download for Google Drive File ID: {file_id}")
        # Run gdown package download utility
        gdown.download(url, output_path, quiet=False)
        print(f"[SYSTEM] Successfully downloaded video to {output_path}")
    except Exception as e:
        print(f"[ERROR] gdown download failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Google Drive download failed: {str(e)}")
        
    return output_path
