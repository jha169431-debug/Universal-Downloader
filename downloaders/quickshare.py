import json
import re

from downloaders.direct import DirectDownloader


class QuickShare:
    def __init__(self, checksum=None):
        self.downloader = DirectDownloader(
            source_name="Samsung Quick Share",
            checksum=checksum,
        )

    def download(self, url):
        response = self.downloader._request(
            url,
            stream=False,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Linux; Android 16; SM-S911B) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/138.0 Mobile Safari/537.36"
                )
            },
        )
        response.raise_for_status()

        try:
            html = response.text
        finally:
            response.close()

        match = re.search(
            r'options\.sharedatacontents\s*=\s*JSON\.parse\(\'(.*?)\'\);',
            html,
            re.DOTALL,
        )

        if not match:
            raise Exception(
                "Unable to locate Quick Share data."
            )

        data = json.loads(match.group(1))
        real_url = data[0]["original"]

        self.downloader.download(real_url)
