#!/usr/bin/env python3
"""Download files or folders from Gofile.io URL."""
import os
import sys
import re
import requests

def download_file(url, out_path, headers=None):
    print(f"Bắt đầu tải: {os.path.basename(out_path)}...", flush=True)
    with requests.get(url, headers=headers, stream=True, timeout=60) as r:
        r.raise_for_status()
        total_size = int(r.headers.get('content-length', 0))
        downloaded = 0
        with open(out_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=2 * 1024 * 1024):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        mb_done = downloaded / (1024 * 1024)
                        mb_total = total_size / (1024 * 1024)
                        print(f"\r  -> Đã tải: {mb_done:.1f} MB / {mb_total:.1f} MB ({percent:.1f}%)", end="", flush=True)
    print(f"\nHoàn tất tải: {os.path.basename(out_path)}", flush=True)

def main():
    if len(sys.argv) < 2:
        sys.exit("Cách dùng: download_gofile.py <gofile_url> [output_dir]")
    
    url = sys.argv[1]
    dest = sys.argv[2] if len(sys.argv) > 2 else "game"
    os.makedirs(dest, exist_ok=True)
    
    m = re.search(r'gofile\.io/d/([a-zA-Z0-9_-]+)', url)
    if not m:
        sys.exit(f"URL Gofile không hợp lệ: {url}")
    content_id = m.group(1)
    
    # Lấy guest account token
    headers = {}
    try:
        acc_res = requests.post("https://api.gofile.io/accounts", timeout=30).json()
        token = acc_res.get("data", {}).get("token", "")
        if token:
            headers["Authorization"] = f"Bearer {token}"
    except Exception as e:
        print(f"Cảnh báo: không thể lấy token guest ({e}), thử tiếp tục không có token...", flush=True)
    
    # Lấy thông tin nội dung
    api_url = f"https://api.gofile.io/contents/{content_id}"
    res = requests.get(api_url, headers=headers, timeout=30).json()
    if res.get("status") != "ok":
        sys.exit(f"Không thể lấy thông tin từ Gofile: {res}")
        
    data = res.get("data", {})
    item_type = data.get("type")
    
    if item_type == "file":
        name = data.get("name")
        file_url = data.get("link") or data.get("directLink")
        if file_url:
            download_file(file_url, os.path.join(dest, name), headers=headers)
    else:
        children = data.get("children", {})
        if not children:
            print("Thư mục Gofile không có file nào.", flush=True)
            return
            
        print(f"Tìm thấy {len(children)} mục trong thư mục Gofile.", flush=True)
        for child_id, info in children.items():
            if info.get("type") == "file":
                name = info.get("name")
                file_url = info.get("link") or info.get("directLink")
                if file_url:
                    download_file(file_url, os.path.join(dest, name), headers=headers)

if __name__ == "__main__":
    main()
