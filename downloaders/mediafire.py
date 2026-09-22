from downloaders.direct import DirectDownloader


class MediaFire:
    """
    MediaFire adapter.

    MediaFire share links are HTML landing pages. The generic
    DirectDownloader resolves the landing page to the real file URL.
    """

    def __init__(self, checksum=None):
        self.downloader = DirectDownloader(
            source_name="MediaFire",
            checksum=checksum,
        )

    def download(self, url):
        self.downloader.download(url)
