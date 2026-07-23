import os
import time
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

        name = os.path.basename(url.split("?")[0])

        return name if name else "download"

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

        # Save to Android Downloads folder
        download_dir = "/storage/emulated/0/Download"
        os.makedirs(download_dir, exist_ok=True)
        filepath = os.path.join(download_dir, filename)

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

                if speed > 0:
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

        self.ui.finish(filepath)
