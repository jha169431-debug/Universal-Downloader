import os
import time
from pathlib import Path

import requests

from terminal_ui import TerminalUI


class DirectDownloader:
    def __init__(self, chunk_size=1024 * 256):
        self.chunk_size = chunk_size
        self.ui = TerminalUI()

    def _filename(self, response, url):
        cd = response.headers.get("Content-Disposition")

        if cd and "filename=" in cd:
            return cd.split("filename=")[-1].strip('"')

        # Prefer the final URL after redirects so the saved name matches
        # the actual file whenever the host redirects to one.
        source_url = response.url or url
        name = os.path.basename(source_url.split("?")[0])

        return name if name else "download"

    def _download_dir(self):
        """
        Pick a writable download directory.

        Priority:
        1. UNIVERSAL_DOWNLOADER_DIR environment override
        2. Mounted BUILD_DRIVE on Linux
        3. Android/Termux Downloads
        4. ~/Downloads fallback
        """
        override = os.environ.get("UNIVERSAL_DOWNLOADER_DIR")

        if override:
            download_dir = Path(override).expanduser()
        else:
            username = os.environ.get("USER") or Path.home().name

            build_drive_candidates = (
                Path("/run/media") / username / "BUILD_DRIVE",
                Path("/media") / username / "BUILD_DRIVE",
            )

            build_drive = next(
                (
                    path
                    for path in build_drive_candidates
                    if path.is_dir()
                ),
                None,
            )

            if build_drive is not None:
                # Keep large ROM/ISO downloads off the system disk.
                download_dir = build_drive / "Downloads"
            else:
                android_downloads = Path(
                    "/storage/emulated/0/Download"
                )

                if (
                    android_downloads.parent.exists()
                    and os.access(
                        android_downloads.parent,
                        os.W_OK,
                    )
                ):
                    download_dir = android_downloads
                else:
                    download_dir = Path.home() / "Downloads"

        download_dir.mkdir(parents=True, exist_ok=True)

        if not os.access(download_dir, os.W_OK):
            raise PermissionError(
                f"Download directory is not writable: "
                f"{download_dir}"
            )

        return download_dir

    def download(self, url):
        response = requests.get(
            url,
            stream=True,
            allow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        response.raise_for_status()

        filename = self._filename(response, url)

        download_dir = self._download_dir()
        filepath = download_dir / filename

        total = int(response.headers.get("Content-Length", 0))
        downloaded = 0

        start_time = time.time()

        with open(filepath, "wb") as f:
            for chunk in response.iter_content(self.chunk_size):

                if not chunk:
                    continue

                f.write(chunk)
                downloaded += len(chunk)

                elapsed = max(time.time() - start_time, 0.001)

                speed = downloaded / elapsed

                if speed > 0 and total > 0:
                    eta = int((total - downloaded) / speed)
                else:
                    eta = 0

                self.ui.draw(
                    filename,
                    downloaded,
                    total,
                    speed / 1024 / 1024,
                    eta
                )

        self.ui.finish(str(filepath))
