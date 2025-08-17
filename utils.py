import subprocess
import os

def ffprobe_get(query, default=None):
    result = subprocess.run(query, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return result.stdout.strip() if result.returncode == 0 and result.stdout.strip() else default

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)
