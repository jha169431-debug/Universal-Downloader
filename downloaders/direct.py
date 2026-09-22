import os
import re
import time
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from terminal_ui import TerminalUI


class DirectDownloader:
    FILE_EXTENSIONS = (
        ".iso",
        ".img",
        ".zip",
        ".7z",
        ".rar",
        ".tar",
        ".tar.gz",
        ".tgz",
        ".xz",
        ".gz",
        ".bz2",
        ".zst",
        ".apk",
        ".exe",
        ".msi",
        ".deb",
        ".rpm",
        ".torrent",
    )

    def __init__(self, chunk_size=1024 * 256):
        self.chunk_size = chunk_size
        self.ui = TerminalUI()
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "Mozilla/5.0"}
        )

    def _filename(self, response, url):
        cd = response.headers.get("Content-Disposition", "")

        filename_star = re.search(
            r"filename\*=UTF-8''([^;]+)",
            cd,
            flags=re.IGNORECASE,
        )
        if filename_star:
            return unquote(filename_star.group(1)).strip('"')

        filename = re.search(
            r'filename="?([^";]+)"?',
            cd,
            flags=re.IGNORECASE,
        )
        if filename:
            return filename.group(1).strip()

        # Prefer the final URL after redirects so the saved name matches
        # the actual file whenever the host redirects to one.
        source_url = response.url or url
        name = os.path.basename(
            urlparse(source_url).path
        )

        return unquote(name) if name else "download"

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

    def _looks_like_file_url(self, url):
        path = urlparse(url).path.lower()

        return any(
            path.endswith(ext)
            for ext in self.FILE_EXTENSIONS
        )

    def _resolve_html_download(self, page_url, html):
        """
        Extract the most likely real download URL from an HTML landing page.

        This handles pages that auto-start a download in the browser or show
        links such as "click here if the download doesn't start".
        """
        soup = BeautifulSoup(html, "html.parser")
        candidates = []

        def add_candidate(raw_url, score):
            if not raw_url:
                return

            raw_url = raw_url.strip()

            if raw_url.startswith(
                ("javascript:", "mailto:", "#")
            ):
                return

            absolute = urljoin(page_url, raw_url)

            if absolute == page_url:
                return

            lowered = absolute.lower()

            if self._looks_like_file_url(absolute):
                score += 100

            if "download." in urlparse(
                absolute
            ).netloc.lower():
                score += 25

            if "download" in lowered:
                score += 15

            candidates.append((score, absolute))

        for link in soup.find_all("a", href=True):
            href = link.get("href")
            text = link.get_text(" ", strip=True).lower()

            score = 0

            if link.has_attr("download"):
                score += 80

            if "click here" in text:
                score += 70

            if "download" in text:
                score += 60

            if "direct" in text:
                score += 40

            add_candidate(href, score)

        # Some sites put the real download URL only inside JavaScript.
        url_pattern = re.compile(
            r'https?://[^\s\'"<>]+',
            flags=re.IGNORECASE,
        )

        for match in url_pattern.findall(html):
            add_candidate(match, 25)

        if not candidates:
            return None

        candidates.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        best_score, best_url = candidates[0]

        # Do not guess from weak navigation links.
        if best_score < 60:
            return None

        return best_url

    def _open_download(self, url, depth=0, referer=None):
        if depth > 3:
            raise RuntimeError(
                "Too many landing-page redirects while "
                "resolving the download."
            )

        headers = {}

        if referer:
            headers["Referer"] = referer

        response = self.session.get(
            url,
            stream=True,
            allow_redirects=True,
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()

        content_type = response.headers.get(
            "Content-Type",
            "",
        ).lower()

        path = urlparse(
            response.url or url
        ).path.lower()

        is_html = (
            "text/html" in content_type
            or path.endswith((".html", ".htm"))
        )

        if not is_html:
            return response

        # HTML landing pages are small enough to inspect before downloading.
        html = response.text
        page_url = response.url or url
        response.close()

        self.ui.start("Resolving download page…")

        resolved_url = self._resolve_html_download(
            page_url,
            html,
        )

        if not resolved_url:
            raise RuntimeError(
                "Received an HTML landing page, but no real "
                "download link could be resolved."
            )

        self.ui.update("Found direct file link…")

        return self._open_download(
            resolved_url,
            depth=depth + 1,
            referer=page_url,
        )

    def download(self, url):
        response = self._open_download(url)

        filename = self._filename(response, url)

        download_dir = self._download_dir()
        filepath = download_dir / filename

        total = int(
            response.headers.get(
                "Content-Length",
                0,
            )
            or 0
        )
        downloaded = 0

        start_time = time.time()

        with open(filepath, "wb") as f:
            for chunk in response.iter_content(
                self.chunk_size
            ):

                if not chunk:
                    continue

                f.write(chunk)
                downloaded += len(chunk)

                elapsed = max(
                    time.time() - start_time,
                    0.001,
                )

                speed = downloaded / elapsed

                if speed > 0 and total > 0:
                    eta = int(
                        (total - downloaded) / speed
                    )
                else:
                    eta = 0

                self.ui.draw(
                    filename,
                    downloaded,
                    total,
                    speed / 1024 / 1024,
                    eta,
                )

        response.close()
        self.ui.finish(str(filepath))
