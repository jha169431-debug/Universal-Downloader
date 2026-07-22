import requests
from bs4 import BeautifulSoup

from downloaders.direct import DirectDownloader


class MediaFire:

    def __init__(self):
        self.session = requests.Session()
        self.downloader = DirectDownloader()

    def get_download_url(self, url):

        response = self.session.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        button = soup.find("a", {"id": "downloadButton"})

        if not button:
            raise Exception("Download button not found.")

        return button["href"]

    def download(self, url):

        real_url = self.get_download_url(url)

        self.downloader.download(real_url)
