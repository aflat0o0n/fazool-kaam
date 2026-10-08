#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to download files directly into Google Drive (designed for Google Colab / standalone use).
"""

import os
import sys
import re
import requests
from pathlib import Path
from urllib.parse import urlparse

def mount_drive():
    """Mount Google Drive if running in Google Colab environment."""
    try:
        from google.colab import drive
        drive_path = Path("/content/drive")
        if not drive_path.exists() or not any(drive_path.iterdir()):
            print("Mounting Google Drive ...")
            drive.mount("/content/drive")
            print("✅ Google Drive mounted at /content/drive.")
        else:
            print("✅ Google Drive is already mounted.")
        return Path("/content/drive/MyDrive")
    except ImportError:
        print("Not running in Google Colab. Downloads will save locally.")
        return Path("./downloads")

def download_file(url: str, output_dir: Path, custom_filename: str = None) -> Path:
    """Download a file from a URL directly into the specified output directory.

    Supports direct HTTP/HTTPS URLs and Google Drive URLs via gdown.
    """
    url = url.strip()
    if not url:
        raise ValueError("URL cannot be empty.")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if custom_filename and custom_filename.strip():
        out_name = custom_filename.strip()
    else:
        out_name = Path(urlparse(url).path).name or "download.bin"

    out_name = re.sub(r'[^A-Za-z0-9._-]', '_', out_name)
    out_path = output_dir / out_name

    print(f"Destination: {out_path}")

    # Google Drive download handling via gdown
    if "drive.google.com" in url:
        try:
            import gdown
            print("Google Drive URL detected — downloading with gdown ...")
            gdown.download(url, str(out_path), fuzzy=True)
            print(f"✅ Downloaded with gdown: {out_path} ({out_path.stat().st_size / 1e6:.1f} MB)")
            return out_path
        except ImportError:
            print("gdown package not installed. Installing gdown ...")
            import subprocess
            subprocess.run([sys.executable, "-m", "pip", "install", "-q", "gdown"], check=True)
            import gdown
            gdown.download(url, str(out_path), fuzzy=True)
            print(f"✅ Downloaded with gdown: {out_path} ({out_path.stat().st_size / 1e6:.1f} MB)")
            return out_path

    # Direct HTTP download
    headers = {
        "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) "
                       "AppleWebKit/537.36 Chrome/131 Safari/537.36"),
        "Accept": "*/*",
    }

    print(f"Downloading from: {url[:80]}...")
    with requests.get(url, headers=headers, stream=True, allow_redirects=True, timeout=(30, 180)) as resp:
        resp.raise_for_status()

        # Check content-disposition header if name is generic
        if out_name in ("download.bin", ""):
            cd = resp.headers.get("content-disposition", "")
            m = re.search(r'filename="?([^";\n]+)"?', cd)
            if m:
                out_name = re.sub(r'[^A-Za-z0-9._-]', '_', m.group(1).strip())
                out_path = output_dir / out_name

        part_file = out_path.with_suffix(out_path.suffix + ".part")
        downloaded_bytes = 0
        total_bytes = int(resp.headers.get('content-length', 0))

        with part_file.open("wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
                    downloaded_bytes += len(chunk)
                    if total_bytes > 0:
                        percent = (downloaded_bytes / total_bytes) * 100
                        sys.stdout.write(f"\rProgress: {percent:.1f}% ({downloaded_bytes / 1e6:.1f} / {total_bytes / 1e6:.1f} MB)")
                        sys.stdout.flush()

        part_file.replace(out_path)
        print(f"\n✅ Download complete: {out_path} ({out_path.stat().st_size / 1e6:.1f} MB)")
        return out_path

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Download files directly into Google Drive.")
    parser.add_argument("url", help="Download URL")
    parser.add_argument("--folder", default="Downloads", help="Subfolder name inside MyDrive (default: Downloads)")
    parser.add_argument("--filename", default=None, help="Custom filename override")

    args = parser.parse_args()

    drive_root = mount_drive()
    target_dir = drive_root / args.folder
    download_file(args.url, target_dir, custom_filename=args.filename)

if __name__ == "__main__":
    main()
