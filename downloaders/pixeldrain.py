import requests
from dataclasses import dataclass
from urllib.parse import quote, unquote, urlparse

from downloaders.direct import DirectDownloader


@dataclass(frozen=True)
class PixelDrainTarget:
    kind: str
    ident: str


class PixelDrain:
    API_ROOT = "https://pixeldrain.com/api"

    CAPTCHA_ERRORS = {
        "file_rate_limited_captcha_required",
        "virus_detected_captcha_required",
        "ip_download_limited_captcha_required",
        "server_overload_captcha_required",
    }

    LIMIT_ERRORS = {
        "hotlink_detected",
        "max_concurrent_downloads",
        "transfer_limit_exceeded",
        "download_limit_exceeded",
    }

    def __init__(self):
        self.downloader = DirectDownloader(
            source_name="PixelDrain"
        )
        self.ui = self.downloader.ui

    @staticmethod
    def supports(url):
        try:
            parsed = urlparse(url)
        except ValueError:
            return False

        if parsed.netloc.lower() not in {
            "pixeldrain.com",
            "www.pixeldrain.com",
        }:
            return False

        parts = [
            unquote(part)
            for part in parsed.path.split("/")
            if part
        ]

        if len(parts) >= 2 and parts[0].lower() in {
            "u",
            "l",
        }:
            return True

        return (
            len(parts) >= 3
            and parts[0].lower() == "api"
            and parts[1].lower() in {"file", "list"}
        )

    @staticmethod
    def parse_target(url):
        parsed = urlparse(url)

        if parsed.netloc.lower() not in {
            "pixeldrain.com",
            "www.pixeldrain.com",
        }:
            raise ValueError(
                "PixelDrain URLs must use pixeldrain.com."
            )

        parts = [
            unquote(part)
            for part in parsed.path.split("/")
            if part
        ]

        if len(parts) >= 2:
            prefix = parts[0].lower()

            if prefix == "u":
                return PixelDrainTarget(
                    kind="file",
                    ident=parts[1],
                )

            if prefix == "l":
                return PixelDrainTarget(
                    kind="list",
                    ident=parts[1],
                )

        if (
            len(parts) >= 3
            and parts[0].lower() == "api"
        ):
            resource = parts[1].lower()
            ident = parts[2]

            if resource == "file":
                return PixelDrainTarget(
                    kind="file",
                    ident=ident,
                )

            if resource == "list":
                return PixelDrainTarget(
                    kind="list",
                    ident=ident,
                )

        raise ValueError(
            "Paste a PixelDrain file or list URL."
        )

    @staticmethod
    def _clean_id(value):
        value = str(value).strip()

        if not value:
            raise ValueError(
                "PixelDrain link has no file/list ID."
            )

        return value

    def _api_url(self, resource, ident, suffix=""):
        ident = quote(
            self._clean_id(ident),
            safe="",
        )

        return (
            f"{self.API_ROOT}/{resource}/{ident}"
            f"{suffix}"
        )

    def _file_download_url(self, file_id):
        return (
            self._api_url("file", file_id)
            + "?download"
        )

    def _viewer_url(self, file_id):
        file_id = quote(
            self._clean_id(file_id),
            safe="",
        )
        return f"https://pixeldrain.com/u/{file_id}"

    def _api_error(self, response, subject):
        value = None
        message = None

        try:
            payload = response.json()
        except (ValueError, requests.JSONDecodeError):
            payload = {}

        if isinstance(payload, dict):
            value = payload.get("value")
            message = payload.get("message")

        if response.status_code == 404:
            return RuntimeError(
                f"PixelDrain {subject} was not found."
            )

        if response.status_code == 451:
            return RuntimeError(
                f"PixelDrain {subject} is unavailable "
                "for legal reasons."
            )

        detail = message or value or (
            f"HTTP {response.status_code}"
        )

        return RuntimeError(
            f"PixelDrain {subject} request failed: "
            f"{detail}"
        )

    def _get_json(self, url, subject):
        response = self.downloader._request(
            url,
            stream=False,
        )

        try:
            if response.status_code >= 400:
                raise self._api_error(
                    response,
                    subject,
                )

            payload = response.json()

            if not isinstance(payload, dict):
                raise RuntimeError(
                    f"PixelDrain returned invalid "
                    f"{subject} metadata."
                )

            return payload
        finally:
            response.close()

    def _get_list(self, list_id):
        self.ui.start("Reading PixelDrain list…")

        payload = self._get_json(
            self._api_url("list", list_id),
            "list",
        )

        files = payload.get("files")

        if not isinstance(files, list):
            raise RuntimeError(
                "PixelDrain list metadata has no files."
            )

        return payload

    def _list_assets(self, payload):
        assets = []

        for item in payload.get("files", []):
            file_id = item.get("id")

            if not file_id:
                continue

            assets.append(
                {
                    "id": file_id,
                    "name": item.get(
                        "name",
                        "unnamed-file",
                    ),
                    "size": int(
                        item.get("size", 0) or 0
                    ),
                }
            )

        return assets

    def _select_list_file(self, payload):
        assets = self._list_assets(payload)

        if not assets:
            raise RuntimeError(
                "This PixelDrain list has no "
                "downloadable files."
            )

        if len(assets) == 1:
            return assets[0]

        title = (
            payload.get("title")
            or "PixelDrain List"
        )

        return self.ui.choose_asset(
            title,
            assets,
            heading="◆ PIXELDRAIN LIST",
            subject_label="List",
            prompt="Choose the PixelDrain file to download.",
        )

    def _translate_download_error(
        self,
        exc,
        file_id,
    ):
        response = getattr(exc, "response", None)

        if response is None:
            return None

        try:
            payload = response.json()
        except (ValueError, requests.JSONDecodeError):
            payload = {}

        value = (
            payload.get("value")
            if isinstance(payload, dict)
            else None
        )
        message = (
            payload.get("message")
            if isinstance(payload, dict)
            else None
        )

        viewer = self._viewer_url(file_id)

        if value in self.CAPTCHA_ERRORS:
            return RuntimeError(
                "PixelDrain requires browser/captcha "
                f"confirmation for this file. Open {viewer}, "
                "complete the check, then retry."
            )

        if value in self.LIMIT_ERRORS:
            detail = message or value
            return RuntimeError(
                "PixelDrain blocked this direct download "
                f"({detail}). Open {viewer} or wait for "
                "the limit to clear, then retry."
            )

        if response.status_code == 451:
            return RuntimeError(
                "PixelDrain file is unavailable for "
                "legal reasons."
            )

        return None

    def _download_file(self, file_id):
        viewer = self._viewer_url(file_id)
        direct_url = self._file_download_url(file_id)

        # Keep PixelDrain's viewer as the referrer for initial and resumed
        # requests. DirectDownloader carries the same referrer into Range
        # recovery automatically.
        self.downloader.session.headers.update(
            {"Referer": viewer}
        )

        try:
            self.downloader.download(direct_url)
        except requests.HTTPError as exc:
            translated = self._translate_download_error(
                exc,
                file_id,
            )

            if translated is not None:
                raise translated from exc

            raise

    def download(self, url):
        target = self.parse_target(url)

        if target.kind == "file":
            self._download_file(target.ident)
            return

        payload = self._get_list(target.ident)
        selected = self._select_list_file(payload)

        self.ui.update(
            f"Selected PixelDrain file: "
            f"{selected['name']}"
        )

        self._download_file(selected["id"])
