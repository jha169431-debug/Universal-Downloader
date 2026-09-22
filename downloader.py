from downloaders.direct import DirectDownloader
from downloaders.gdrive import GoogleDrive
from downloaders.github import GitHubRelease
from downloaders.mediafire import MediaFire
from downloaders.pixeldrain import PixelDrain
from downloaders.quickshare import QuickShare
from terminal_ui import TerminalUI


def detect_source(url):
    lowered = url.lower()

    if "drive.google.com" in lowered:
        return "Google Drive", GoogleDrive

    if "mediafire.com" in lowered:
        return "MediaFire", MediaFire

    if "quickshare.samsungcloud.com" in lowered:
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
        url = input("Paste URL  ›  ").strip()

        if not url:
            ui.error("No URL entered")
            return 1

        source_name, downloader_cls = detect_source(url)
        ui.source_found(source_name)

        downloader_cls().download(url)
        return 0

    except KeyboardInterrupt:
        ui.cancelled()
        return 130

    except Exception as exc:
        ui.error(str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
