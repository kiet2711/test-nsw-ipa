#!/usr/bin/env python3
"""Download files or folders from Gofile.io URL."""
import hashlib
import os
import re
import sys
import time
import requests

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
LANGUAGE = "en-US"
SALT = "12af056dacea0b"

def download_file(session, url, out_path, token):
    filename = os.path.basename(out_path)
    print(f"Downloading: {filename}...", flush=True)
    
    headers = {
        "User-Agent": USER_AGENT,
        "Referer": "https://gofile.io/",
        "Cookie": f"accountToken={token}",
    }
    
    with session.get(url, headers=headers, stream=True, timeout=120) as r:
        r.raise_for_status()
        total_size = int(r.headers.get("content-length", 0))
        downloaded = 0
        last_print = 0
        
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=4 * 1024 * 1024):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    now = time.time()
                    if now - last_print > 1.0 or downloaded == total_size:
                        last_print = now
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            mb_done = downloaded / (1024 * 1024)
                            mb_total = total_size / (1024 * 1024)
                            print(f"\r  -> Progress: {mb_done:.1f} MB / {mb_total:.1f} MB ({percent:.1f}%)", end="", flush=True)
    print(f"\nFinished: {filename}\n", flush=True)

def main():
    if len(sys.argv) < 2:
        sys.exit("Usage: python download_gofile.py <gofile_url> [destination_dir]")
        
    url = sys.argv[1].strip()
    dest = sys.argv[2] if len(sys.argv) > 2 else "game"
    os.makedirs(dest, exist_ok=True)
    
    m = re.search(r"gofile\.io/d/([a-zA-Z0-9_-]+)", url)
    if not m:
        sys.exit(f"Invalid Gofile URL: {url}")
    content_id = m.group(1)
    
    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept-Language": "en-US,en;q=0.5",
    })
    
    print(f"Initializing Gofile session for folder: {content_id}...", flush=True)
    
    # 1. Access landing page for initial cookies
    try:
        session.get(f"https://gofile.io/d/{content_id}", timeout=30)
    except Exception as e:
        print(f"Warning: landing page visit failed: {e}", flush=True)
    
    # 2. Create guest account and retrieve token
    token = ""
    try:
        acc_res = session.post("https://api.gofile.io/accounts", timeout=30).json()
        token = acc_res.get("data", {}).get("token", "")
        if token:
            session.cookies.set("accountToken", token, domain=".gofile.io")
    except Exception as e:
        sys.exit(f"Error creating Gofile guest account: {e}")
    
    if not token:
        sys.exit("Failed to get account token from Gofile API.")
    
    # 3. Calculate dynamic Website Token (wt)
    time_slot = int(time.time()) // 14400
    raw_token = f"{USER_AGENT}::{LANGUAGE}::{token}::{time_slot}::{SALT}"
    wt = hashlib.sha256(raw_token.encode()).hexdigest()
    
    # 4. Fetch content listing
    api_headers = {
        "X-BL": LANGUAGE,
        "X-Website-Token": wt,
        "Authorization": f"Bearer {token}",
        "Referer": f"https://gofile.io/d/{content_id}",
    }
    
    api_url = f"https://api.gofile.io/contents/{content_id}"
    res = session.get(api_url, headers=api_headers, timeout=30).json()
    if res.get("status") != "ok":
        sys.exit(f"Failed to get Gofile content details: {res}")
    
    data = res.get("data", {})
    item_type = data.get("type")
    
    if item_type == "file":
        name = data.get("name")
        file_url = data.get("link") or data.get("directLink")
        if file_url:
            download_file(session, file_url, os.path.join(dest, name), token)
    else:
        children = data.get("children", {})
        if not children:
            print("Gofile folder is empty.", flush=True)
            return
            
        print(f"Found {len(children)} files in Gofile folder. Starting downloads...", flush=True)
        for child_id, info in children.items():
            if info.get("type") == "file":
                name = info.get("name")
                file_url = info.get("link") or info.get("directLink")
                if file_url:
                    download_file(session, file_url, os.path.join(dest, name), token)

if __name__ == "__main__":
    main()
