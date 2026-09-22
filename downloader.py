import argparse

from checksum import ChecksumMismatch, parse_checksum
from downloaders.direct import DirectDownloader
from downloaders.gdrive import GoogleDrive
from downloaders.mediafire import MediaFire
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

    return "Direct URL", DirectDownloader


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Universal Downloader by NPL ROM. "
            "Pass a URL directly or omit it for interactive mode."
        ),
    )
    parser.add_argument(
        "url",
        nargs="?",
        help="URL to download",
    )

    checksum_group = parser.add_mutually_exclusive_group()
    checksum_group.add_argument(
        "--sha256",
        metavar="HASH",
        help="verify the completed file against a SHA-256 hash",
    )
    checksum_group.add_argument(
        "--sha1",
        metavar="HASH",
        help="verify the completed file against a SHA-1 hash",
    )
    checksum_group.add_argument(
        "--md5",
        metavar="HASH",
        help="verify the completed file against an MD5 hash",
    )

    return parser


def checksum_from_args(args):
    if args.sha256:
        return parse_checksum("sha256", args.sha256)

    if args.sha1:
        return parse_checksum("sha1", args.sha1)

    if args.md5:
        return parse_checksum("md5", args.md5)

    return None


def main():
    args = build_parser().parse_args()
    ui = TerminalUI()
    ui.welcome()

    try:
        checksum = checksum_from_args(args)

        if args.url:
            url = args.url.strip()
        else:
            url = input("Paste URL  ›  ").strip()

        if not url:
            ui.error("No URL entered")
            return

        source_name, downloader_cls = detect_source(url)
        ui.source_found(source_name)

        downloader_cls(
            checksum=checksum,
        ).download(url)

    except ChecksumMismatch as exc:
        ui.checksum_failed(
            exc.spec.label,
            exc.spec.expected,
            exc.actual,
            path=str(
                exc.quarantined_path
                or exc.file_path
            ),
        )

    except ValueError as exc:
        ui.error(str(exc))

    except KeyboardInterrupt:
        ui.cancelled()

    except Exception as exc:
        ui.error(str(exc))


if __name__ == "__main__":
    main()
