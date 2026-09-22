from downloaders.direct import DirectDownloader


class MediaFire:
    """
    MediaFire adapter.

    MediaFire share links are HTML landing pages. The generic
    DirectDownloader already knows how to resolve download landing pages
    to the real file URL, so keep MediaFire routing thin instead of
    depending on one brittle HTML element such as #downloadButton.
    """

    def __init__(self):
        self.downloader = DirectDownloader()

    def download(self, url):
        self.downloader.download(url)
