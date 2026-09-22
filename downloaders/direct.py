import os
import re
import time
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from terminal_ui import TerminalUI


class DirectDownloader:
    RETRYABLE_STATUS = {
        408,
        425,
        429,
        500,
        502,
        503,
        504,
    }
    MAX_RETRIES = 5
    MAX_BACKOFF = 16
    REQUEST_TIMEOUT = (10, 30)

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

    def __init__(
        self,
        chunk_size=1024 * 256,
        source_name="Direct URL",
    ):
        self.chunk_size = chunk_size
        self.source_name = source_name
        self.ui = TerminalUI()
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0",
                # Keep byte counts stable for HTTP Range resumes.
                "Accept-Encoding": "identity",
            }
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

        source_url = response.url or url
        name = os.path.basename(
            urlparse(source_url).path
        )

        return unquote(name) if name else "download"

    def _download_dir(self):
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

    def _retry_delay(self, retry_number, response=None):
        if response is not None:
            retry_after = response.headers.get("Retry-After")

            if retry_after:
                try:
                    return min(
                        max(float(retry_after), 0.0),
                        self.MAX_BACKOFF,
                    )
                except ValueError:
                    pass

        return min(
            2 ** max(retry_number - 1, 0),
            self.MAX_BACKOFF,
        )

    def _request(
        self,
        url,
        *,
        headers=None,
        stream=True,
        allow_redirects=True,
    ):
        """
        Make a GET request with bounded exponential backoff.

        This covers connection failures, timeouts and transient HTTP
        responses before a stream begins. Mid-stream recovery is handled
        separately with HTTP Range so downloaded bytes are not discarded.
        """
        last_error = None

        for attempt in range(self.MAX_RETRIES + 1):
            try:
                response = self.session.get(
                    url,
                    stream=stream,
                    allow_redirects=allow_redirects,
                    headers=headers or {},
                    timeout=self.REQUEST_TIMEOUT,
                )
            except requests.RequestException as exc:
                last_error = exc

                if attempt >= self.MAX_RETRIES:
                    raise

                retry_number = attempt + 1
                delay = self._retry_delay(retry_number)
                self.ui.update(
                    f"Network retry {retry_number}/"
                    f"{self.MAX_RETRIES} in {delay:g}s…"
                )
                time.sleep(delay)
                continue

            if (
                response.status_code
                in self.RETRYABLE_STATUS
                and attempt < self.MAX_RETRIES
            ):
                retry_number = attempt + 1
                delay = self._retry_delay(
                    retry_number,
                    response=response,
                )
                response.close()

                self.ui.update(
                    f"Server retry {retry_number}/"
                    f"{self.MAX_RETRIES} in {delay:g}s…"
                )
                time.sleep(delay)
                continue

            return response

        if last_error is not None:
            raise last_error

        raise RuntimeError("Request failed after retries.")

    def _looks_like_file_url(self, url):
        path = urlparse(url).path.lower()

        return any(
            path.endswith(ext)
            for ext in self.FILE_EXTENSIONS
        )

    def _resolve_html_download(self, page_url, html):
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

        response = self._request(
            url,
            stream=True,
            allow_redirects=True,
            headers=headers,
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

    def _content_range(self, response):
        value = response.headers.get("Content-Range", "")

        match = re.match(
            r"bytes\s+(\d+)-(\d+)/(\d+|\*)",
            value,
            flags=re.IGNORECASE,
        )

        if not match:
            return None, None, None

        start = int(match.group(1))
        end = int(match.group(2))
        total = (
            None
            if match.group(3) == "*"
            else int(match.group(3))
        )

        return start, end, total

    def _unsatisfied_total(self, response):
        value = response.headers.get("Content-Range", "")

        match = re.match(
            r"bytes\s+\*/(\d+)",
            value,
            flags=re.IGNORECASE,
        )

        return int(match.group(1)) if match else None

    def _response_total(self, response, resume_from=0):
        _, _, content_range_total = self._content_range(
            response
        )

        if content_range_total is not None:
            return content_range_total

        content_length = int(
            response.headers.get("Content-Length", 0)
            or 0
        )

        if response.status_code == 206 and content_length:
            return resume_from + content_length

        return content_length

    def _fresh_response(self, url):
        response = self._open_download(url)
        total = self._response_total(response)
        return response, total

    def _resume_response(
        self,
        file_url,
        resume_from,
        referer=None,
    ):
        headers = {
            "Range": f"bytes={resume_from}-",
        }

        if referer:
            headers["Referer"] = referer

        return self._request(
            file_url,
            stream=True,
            allow_redirects=True,
            headers=headers,
        )

    def download(self, url):
        response, total = self._fresh_response(url)

        filename = self._filename(response, url)
        download_dir = self._download_dir()
        filepath = download_dir / filename
        partpath = Path(f"{filepath}.part")

        if filepath.exists():
            response.close()
            raise FileExistsError(
                f"File already exists: {filepath}"
            )

        resume_from = (
            partpath.stat().st_size
            if partpath.exists()
            else 0
        )

        # If an old .part is already exactly complete, finalize it without
        # transferring the same file again.
        if total > 0 and resume_from == total:
            response.close()
            self.ui.update(
                "Partial file already complete; finalizing…"
            )
            os.replace(partpath, filepath)

            self.ui.finish(
                str(filepath),
                size=resume_from,
                elapsed=0,
                avg_speed=0,
                source=self.source_name,
            )
            return

        # A partial file larger than the remote object cannot be resumed
        # safely. Keep the final name protected and restart the .part file.
        if total > 0 and resume_from > total:
            self.ui.update(
                "Partial file is invalid; restarting…"
            )
            partpath.unlink(missing_ok=True)
            resume_from = 0

        if resume_from > 0:
            file_url = response.url or url
            referer = response.request.headers.get("Referer")
            response.close()

            self.ui.resume_found(resume_from)

            range_response = self._resume_response(
                file_url,
                resume_from,
                referer=referer,
            )

            if range_response.status_code == 416:
                remote_total = self._unsatisfied_total(
                    range_response
                )
                range_response.close()

                if (
                    remote_total is not None
                    and resume_from == remote_total
                ):
                    os.replace(partpath, filepath)
                    self.ui.finish(
                        str(filepath),
                        size=resume_from,
                        elapsed=0,
                        avg_speed=0,
                        source=self.source_name,
                    )
                    return

                self.ui.update(
                    "Resume rejected; restarting safely…"
                )
                partpath.unlink(missing_ok=True)
                resume_from = 0
                response, total = self._fresh_response(url)

            elif range_response.status_code == 206:
                start, _, remote_total = self._content_range(
                    range_response
                )

                if start != resume_from:
                    range_response.close()
                    self.ui.update(
                        "Resume range mismatch; restarting safely…"
                    )
                    partpath.unlink(missing_ok=True)
                    resume_from = 0
                    response, total = self._fresh_response(url)
                else:
                    response = range_response
                    total = (
                        remote_total
                        if remote_total is not None
                        else self._response_total(
                            response,
                            resume_from=resume_from,
                        )
                    )

            elif range_response.status_code == 200:
                # The server ignored Range. Reuse the full 200 response,
                # but never append it to the partial file.
                content_type = range_response.headers.get(
                    "Content-Type",
                    "",
                ).lower()

                if "text/html" in content_type:
                    range_response.close()
                    response, total = self._fresh_response(url)
                else:
                    response = range_response
                    total = self._response_total(response)

                self.ui.update(
                    "Server does not support resume; restarting…"
                )
                partpath.unlink(missing_ok=True)
                resume_from = 0

            else:
                try:
                    range_response.raise_for_status()
                finally:
                    range_response.close()

        downloaded = resume_from
        transferred_this_session = 0

        start_time = time.time()
        sample_time = start_time
        sample_bytes = downloaded
        smoothed_speed = None

        mode = "ab" if resume_from else "wb"

        try:
            with open(partpath, mode) as f:
                for chunk in response.iter_content(
                    self.chunk_size
                ):
                    if not chunk:
                        continue

                    f.write(chunk)
                    downloaded += len(chunk)
                    transferred_this_session += len(chunk)

                    now = time.time()
                    sample_elapsed = max(
                        now - sample_time,
                        0.001,
                    )
                    sample_delta = downloaded - sample_bytes
                    instant_speed = (
                        sample_delta / sample_elapsed
                    )

                    if smoothed_speed is None:
                        smoothed_speed = instant_speed
                    else:
                        alpha = 0.18
                        smoothed_speed = (
                            alpha * instant_speed
                            + (1 - alpha) * smoothed_speed
                        )

                    sample_time = now
                    sample_bytes = downloaded

                    if (
                        smoothed_speed > 0
                        and total > 0
                    ):
                        eta = int(
                            (total - downloaded)
                            / smoothed_speed
                        )
                    else:
                        eta = 0

                    self.ui.draw(
                        filename,
                        downloaded,
                        total,
                        smoothed_speed / 1024 / 1024,
                        eta,
                        source=self.source_name,
                        destination=str(download_dir),
                        resume_from=resume_from,
                    )

                # Flush the completed partial before the atomic rename.
                f.flush()
                os.fsync(f.fileno())
        finally:
            response.close()

        if total > 0 and downloaded != total:
            raise RuntimeError(
                "Download ended before the expected file size "
                f"was reached ({downloaded}/{total} bytes). "
                f"Partial file kept at: {partpath}"
            )

        # A completed file becomes visible under its final name only now.
        os.replace(partpath, filepath)

        elapsed = max(time.time() - start_time, 0.001)
        avg_speed = (
            transferred_this_session
            / elapsed
            / 1024
            / 1024
        )

        self.ui.finish(
            str(filepath),
            size=downloaded,
            elapsed=elapsed,
            avg_speed=avg_speed,
            source=self.source_name,
        )
