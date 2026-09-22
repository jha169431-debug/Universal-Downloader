from downloaders.direct import DirectDownloader
from downloaders.gdrive import GoogleDrive
from downloaders.github import GitHubRelease
from downloaders.mediafire import MediaFire
from downloaders.quickshare import QuickShare
from terminal_ui import TerminalUI


def detect_source(url):
    lowered = url.lower()

    if "github.com/" in lowered:
        from urllib.parse import urlparse

        parts = [
            part
            for part in urlparse(url).path.split("/")
            if part
        ]

        if (
            len(parts) == 2
            or (
                len(parts) >= 3
                and parts[2] == "releases"
            )
        ):
            return "GitHub Releases", GitHubRelease

    if "drive.google.com" in lowered:
        return "Google Drive", GoogleDrive

    if "mediafire.com" in lowered:
        return "MediaFire", MediaFire

    if "quickshare.samsungcloud.com" in lowered:
        return "Samsung Quick Share", QuickShare

    return "Direct URL", DirectDownloader


def main():
    ui = TerminalUI()
    ui.welcome()

    try:
        url = input("Paste URL  ›  ").strip()

        if not url:
            ui.error("No URL entered")
            return

        source_name, downloader_cls = detect_source(url)
        ui.source_found(source_name)

        downloader_cls().download(url)

    except KeyboardInterrupt:
        ui.cancelled()

    except Exception as exc:
        ui.error(str(exc))


if __name__ == "__main__":
    main()
