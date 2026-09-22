import json
import re

import requests

from downloaders.direct import DirectDownloader


class QuickShare:
    def __init__(self):
        self.session = requests.Session()
        self.downloader = DirectDownloader(
            source_name="Samsung Quick Share"
        )

    def download(self, url):
        html = self.session.get(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Linux; Android 16; SM-S911B) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/138.0 Mobile Safari/537.36"
                )
            },
            timeout=30,
        ).text

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
