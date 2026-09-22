import os
import re
import time
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from checksum import ChecksumMismatch, hash_file
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
        checksum=None,
    ):
        self.chunk_size = chunk_size
        self.source_name = source_name
        self.checksum = checksum
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

    def _quarantine_path(self, path):
        path = Path(path)
        raw = str(path)

        if raw.endswith(".part"):
            raw = raw[:-5]

        candidate = Path(f"{raw}.corrupt")
        index = 1

        while candidate.exists():
            candidate = Path(
                f"{raw}.corrupt.{index}"
            )
            index += 1

        return candidate

    def _verify_checksum(
        self,
        path,
        *,
        display_name=None,
    ):
        if self.checksum is None:
            return None

        path = Path(path)
        spec = self.checksum
        shown_name = (
            display_name
            if display_name is not None
            else path.name
        )

        actual = hash_file(
            path,
            spec.algorithm,
            progress=lambda processed, total: (
                self.ui.checksum_progress(
                    shown_name,
                    processed,
                    total,
                    spec.label,
                )
            ),
        )

        if actual != spec.expected:
            quarantined = self._quarantine_path(path)
            os.replace(path, quarantined)

            raise ChecksumMismatch(
                spec,
                actual,
                path,
                quarantined_path=quarantined,
            )

        return actual

    def _finalize_part(
        self,
        partpath,
        filepath,
        *,
        size,
        elapsed,
        avg_speed,
    ):
        actual = self._verify_checksum(
            partpath,
            display_name=filepath.name,
        )

        os.replace(partpath, filepath)

        self.ui.finish(
            str(filepath),
            size=size,
            elapsed=elapsed,
            avg_speed=avg_speed,
            source=self.source_name,
            checksum_label=(
                self.checksum.label
                if self.checksum is not None
                else None
            ),
            checksum_digest=actual,
        )

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

    def _recover_download_response(
        self,
        original_url,
        file_url,
        offset,
        referer=None,
    ):
        """
        Reopen a transfer at offset.

        If a signed/direct URL expired, resolve the original share URL again.
        If the server ignores Range or returns an invalid range, return a
        fresh full response and tell the caller to restart the .part safely.
        """
        response = self._resume_response(
            file_url,
            offset,
            referer=referer,
        )

        if response.status_code in (401, 403, 404):
            response.close()
            self.ui.update("Refreshing download link…")

            fresh, fresh_total = self._fresh_response(
                original_url
            )
            file_url = fresh.url or original_url
            referer = fresh.request.headers.get("Referer")
            fresh.close()

            response = self._resume_response(
                file_url,
                offset,
                referer=referer,
            )

        if response.status_code == 206:
            start, _, remote_total = self._content_range(
                response
            )

            if start != offset:
                response.close()
                self.ui.update(
                    "Range mismatch; restarting safely…"
                )
                fresh, fresh_total = self._fresh_response(
                    original_url
                )
                return (
                    fresh,
                    fresh_total,
                    fresh.url or original_url,
                    fresh.request.headers.get("Referer"),
                    True,
                    False,
                )

            total = (
                remote_total
                if remote_total is not None
                else self._response_total(
                    response,
                    resume_from=offset,
                )
            )
            return (
                response,
                total,
                response.url or file_url,
                response.request.headers.get("Referer")
                or referer,
                False,
                False,
            )

        if response.status_code == 416:
            remote_total = self._unsatisfied_total(response)
            response.close()

            if (
                remote_total is not None
                and offset == remote_total
            ):
                return (
                    None,
                    remote_total,
                    file_url,
                    referer,
                    False,
                    True,
                )

            self.ui.update(
                "Resume rejected; restarting safely…"
            )
            fresh, fresh_total = self._fresh_response(
                original_url
            )
            return (
                fresh,
                fresh_total,
                fresh.url or original_url,
                fresh.request.headers.get("Referer"),
                True,
                False,
            )

        if response.status_code == 200:
            content_type = response.headers.get(
                "Content-Type",
                "",
            ).lower()

            if "text/html" in content_type:
                response.close()
                fresh, fresh_total = self._fresh_response(
                    original_url
                )
                response = fresh
                total = fresh_total
            else:
                total = self._response_total(response)

            return (
                response,
                total,
                response.url or file_url,
                response.request.headers.get("Referer")
                or referer,
                True,
                False,
            )

        try:
            response.raise_for_status()
        except Exception:
            response.close()
            raise

        raise RuntimeError(
            f"Unexpected resume response: "
            f"HTTP {response.status_code}"
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
            self._finalize_part(
                partpath,
                filepath,
                size=resume_from,
                elapsed=0,
                avg_speed=0,
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

        file_url = response.url or url
        referer = response.request.headers.get("Referer")

        if resume_from > 0:
            response.close()
            self.ui.resume_found(resume_from)

            (
                response,
                total,
                file_url,
                referer,
                restart,
                complete,
            ) = self._recover_download_response(
                url,
                file_url,
                resume_from,
                referer=referer,
            )

            if complete:
                self._finalize_part(
                    partpath,
                    filepath,
                    size=resume_from,
                    elapsed=0,
                    avg_speed=0,
                )
                return

            if restart:
                self.ui.update(
                    "Server cannot resume; restarting safely…"
                )
                partpath.unlink(missing_ok=True)
                resume_from = 0

        downloaded = resume_from
        transferred_this_session = 0
        recovery_attempts = 0

        start_time = time.time()
        sample_time = start_time
        sample_bytes = downloaded
        smoothed_speed = None

        mode = "ab" if resume_from else "wb"

        with open(partpath, mode) as f:
            while True:
                stream_error = None

                try:
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
                        sample_delta = (
                            downloaded - sample_bytes
                        )
                        instant_speed = (
                            sample_delta / sample_elapsed
                        )

                        if smoothed_speed is None:
                            smoothed_speed = instant_speed
                        else:
                            alpha = 0.18
                            smoothed_speed = (
                                alpha * instant_speed
                                + (1 - alpha)
                                * smoothed_speed
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
                            smoothed_speed
                            / 1024
                            / 1024,
                            eta,
                            source=self.source_name,
                            destination=str(
                                download_dir
                            ),
                            resume_from=resume_from,
                        )

                except requests.RequestException as exc:
                    stream_error = exc

                finally:
                    response.close()

                # A normal EOF is completion when the size is unknown,
                # or when all advertised bytes have arrived.
                if stream_error is None:
                    if total <= 0 or downloaded >= total:
                        break

                recovery_attempts += 1

                if recovery_attempts > self.MAX_RETRIES:
                    message = (
                        "Network recovery exhausted after "
                        f"{self.MAX_RETRIES} attempts. "
                        f"Partial file kept at: {partpath}"
                    )

                    if stream_error is not None:
                        raise RuntimeError(
                            message
                        ) from stream_error

                    raise RuntimeError(message)

                # Persist everything received before attempting a new
                # connection. This also makes a sudden process exit safer.
                f.flush()
                os.fsync(f.fileno())

                delay = self._retry_delay(
                    recovery_attempts
                )
                self.ui.update(
                    f"Connection interrupted • recovery "
                    f"{recovery_attempts}/"
                    f"{self.MAX_RETRIES} in {delay:g}s…"
                )
                time.sleep(delay)

                (
                    response,
                    recovered_total,
                    file_url,
                    referer,
                    restart,
                    complete,
                ) = self._recover_download_response(
                    url,
                    file_url,
                    downloaded,
                    referer=referer,
                )

                if complete:
                    total = recovered_total
                    break

                if restart:
                    self.ui.update(
                        "Range unavailable; restarting safely…"
                    )
                    f.seek(0)
                    f.truncate(0)
                    f.flush()
                    os.fsync(f.fileno())

                    downloaded = 0
                    resume_from = 0

                total = recovered_total

                # Do not let the pause/reconnect interval distort the
                # displayed speed or ETA.
                sample_time = time.time()
                sample_bytes = downloaded
                smoothed_speed = None

            # Flush the completed partial before the atomic rename.
            f.flush()
            os.fsync(f.fileno())

        if total > 0 and downloaded != total:
            raise RuntimeError(
                "Download ended before the expected file size "
                f"was reached ({downloaded}/{total} bytes). "
                f"Partial file kept at: {partpath}"
            )

        elapsed = max(time.time() - start_time, 0.001)
        avg_speed = (
            transferred_this_session
            / elapsed
            / 1024
            / 1024
        )

        # Verify before the atomic rename. A checksum mismatch is
        # quarantined as *.corrupt and never appears as a valid file.
        self._finalize_part(
            partpath,
            filepath,
            size=downloaded,
            elapsed=elapsed,
            avg_speed=avg_speed,
        )
