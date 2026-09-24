from urllib.parse import urlparse

from downloaders.direct import DirectDownloader, DownloadCancelled
from downloaders.gdrive import GoogleDrive
from downloaders.github import GitHubRelease
from downloaders.mediafire import MediaFire
from downloaders.pixeldrain import PixelDrain
from downloaders.quickshare import QuickShare
from terminal_ui import TerminalUI


APP_VERSION = "5.4"


def normalize_url(url):
    """Trim user input and validate that it is an HTTP(S) URL."""
    url = url.strip()

    if not url:
        raise ValueError("No URL entered")

    parsed = urlparse(url)

    if parsed.scheme.lower() not in {"http", "https"}:
        raise ValueError("URL must start with http:// or https://")

    if not parsed.netloc:
        raise ValueError("Invalid URL")

    return url


def detect_source(url):
    """Return a display name and downloader class for the supplied URL."""
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()

    if host == "drive.google.com" or host.endswith(".drive.google.com"):
        return "Google Drive", GoogleDrive

    if host == "mediafire.com" or host.endswith(".mediafire.com"):
        return "MediaFire", MediaFire

    if host == "quickshare.samsungcloud.com":
        return "Samsung Quick Share", QuickShare

    if GitHubRelease.supports(url):
        return "GitHub Releases", GitHubRelease

    if PixelDrain.supports(url):
        return "PixelDrain", PixelDrain

    return "Direct URL", DirectDownloader


def main():
    ui = TerminalUI()
    ui.welcome()

    try:
        url = normalize_url(input("Paste URL  ›  "))

        source_name, downloader_cls = detect_source(url)
        ui.source_found(source_name)

        downloader = downloader_cls()
        downloader.download(url)

        return 0

    except DownloadCancelled:
        return 130

    except KeyboardInterrupt:
        ui.cancelled()
        return 130

    except Exception as exc:
        ui.error(str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
