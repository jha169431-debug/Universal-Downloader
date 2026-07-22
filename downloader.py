from downloaders.direct import DirectDownloader
from downloaders.gdrive import GoogleDrive
from downloaders.mediafire import MediaFire
from downloaders.quickshare import QuickShare


APP_NAME = "Universal Downloader"
AUTHOR = "NPL🇳🇵ROM™"
VERSION = "2.0"


def banner():
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print()
    print(f"          {APP_NAME}")
    print(f"             by {AUTHOR}")
    print(f"                  v{VERSION}")
    print()
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print()


def main():
    banner()

    url = input("🔗 Paste URL : ").strip()

    print()
    print("🔍 Detecting source...")
    print()

    try:
        if "drive.google.com" in url:
            print("✅ Google Drive detected\n")
            GoogleDrive().download(url)

        elif "mediafire.com" in url:
            print("✅ MediaFire detected\n")
            MediaFire().download(url)

        elif "quickshare.samsungcloud.com" in url:
            print("✅ Samsung Quick Share detected\n")
            QuickShare().download(url)

        else:
            print("✅ Direct URL detected\n")
            DirectDownloader().download(url)

    except KeyboardInterrupt:
        print("\n❌ Download cancelled by user.")

    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
