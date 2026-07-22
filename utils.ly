import os
import re
import time
import requests
from tqdm import tqdm

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"
}

DOWNLOAD_DIR = os.path.expanduser("~/storage/downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def format_size(size):
    size = float(size)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


def download(url, filename=None, headers=None):
    if headers is None:
        headers = HEADERS

    print("\n📡 Connecting...\n")

    r = requests.get(url, stream=True, headers=headers)

    if filename is None:
        cd = r.headers.get("Content-Disposition")

        if cd:
            m = re.search(r'filename="?([^"]+)"?', cd)
            if m:
                filename = m.group(1)

        if not filename:
            filename = url.split("/")[-1].split("?")[0]

    filepath = os.path.join(DOWNLOAD_DIR, filename)

    total = int(r.headers.get("content-length", 0))

    print(f"📄 File : {filename}")
    print(f"📦 Size : {format_size(total)}")
    print(f"📂 Save : {filepath}\n")

    start = time.time()
    downloaded = 0

    with open(filepath, "wb") as f, tqdm(
        total=total,
        desc="⬇ Downloading",
        unit="B",
        unit_scale=True,
        unit_divisor=1024,
        dynamic_ncols=True,
    ) as bar:

        for chunk in r.iter_content(chunk_size=8192):
            if not chunk:
                continue

            f.write(chunk)

            chunk_size = len(chunk)
            downloaded += chunk_size

            elapsed = time.time() - start

            if elapsed > 0:
                speed = downloaded / elapsed

                if total > 0:
                    eta = (total - downloaded) / speed
                else:
                    eta = 0

                bar.set_postfix({
                    "⚡": f"{format_size(speed)}/s",
                    "ETA": f"{int(eta//60):02d}:{int(eta%60):02d}"
                })

            bar.update(chunk_size)

    elapsed = time.time() - start
    avg_speed = downloaded / elapsed if elapsed > 0 else 0

    mins = int(elapsed // 60)
    secs = int(elapsed % 60)

    print("\n" + "=" * 55)
    print("✅ Download completed successfully!")
    print(f"📂 Saved To : {filepath}")
    print(f"⚡ Avg Speed : {format_size(avg_speed)}/s")
    print(f"🕒 Time Taken: {mins:02d}:{secs:02d}")
    print("=" * 55)

    return filepath
