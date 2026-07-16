import sys
import subprocess
import re
import os
import requests
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

def get_drive_filename(file_id: str) -> str:
    """Retrieve the real original filename of a Google Drive file using headers or HTML parsing."""
    url = f"https://drive.google.com/uc?id={file_id}"
    try:
        response = requests.get(url, stream=True)
        cd = response.headers.get('content-disposition')
        if cd:
            filenames = re.findall('filename="(.+?)"', cd)
            if filenames:
                return filenames[0]
        
        # Read the warning page HTML body if redirect occurs
        html = response.raw.read(100000).decode('utf-8', errors='ignore')
        
        # Match inside the <span class="uc-name-size"> link element
        match = re.search(r'class="uc-name-size"[^>]*>\s*<a[^>]*>([^<]+)</a>', html)
        if match:
            return match.group(1).strip()
            
        match_title = re.search(r'<title>Google Drive - (.+?)</title>', html)
        if match_title and "Virus scan" not in match_title.group(1):
            return match_title.group(1).strip()
    except Exception as e:
        print(f"[WARNING] Failed to extract filename from Drive headers: {str(e)}")
    return f"{file_id}.mp4"

def download_drive_file(file_id: str) -> str:
    # Strict validation guard to prevent command injection/path traversal
    if not re.match(r"^[a-zA-Z0-9-_]+$", file_id):
        raise HTTPException(status_code=400, detail="Invalid File ID format")
    
    # Resolve absolute path to the data/videos folder in the core directory
    base_dir = os.path.dirname(os.path.abspath(__file__))
    videos_dir = os.path.join(base_dir, "data", "videos")
    os.makedirs(videos_dir, exist_ok=True)
    
    # Get the real Google Drive filename dynamically
    real_filename = get_drive_filename(file_id)
    output_path = os.path.join(videos_dir, real_filename)
    url = f"https://drive.google.com/uc?id={file_id}"
    
    # If the file already exists, return it directly to avoid duplicate downloads
    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
        print(f"[SYSTEM] File {real_filename} already exists locally. Skipping download.")
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
