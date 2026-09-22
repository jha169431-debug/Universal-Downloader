import os
import time
from pathlib import Path

import gdown

from downloaders.direct import DirectDownloader


class GoogleDrive:
    def __init__(self, checksum=None):
        self.helper = DirectDownloader(
            source_name="Google Drive",
            checksum=checksum,
        )

    def download(self, url):
        download_dir = self.helper._download_dir()
        previous_dir = Path.cwd()
        started = time.time()

        # gdown discovers the Drive filename itself. Run it inside our chosen
        # destination so Google Drive follows the same BUILD_DRIVE policy as
        # every other source.
        try:
            os.chdir(download_dir)
            output = gdown.download(
                url,
                quiet=False,
                fuzzy=True,
            )
        finally:
            os.chdir(previous_dir)

        if not output:
            raise Exception("Google Drive download failed.")

        output_path = Path(output)
        if not output_path.is_absolute():
            output_path = download_dir / output_path

        if not output_path.exists():
            raise Exception(
                "Google Drive finished but the output file "
                "could not be located."
            )

        size = output_path.stat().st_size
        elapsed = max(time.time() - started, 0.001)
        avg_speed = size / elapsed / 1024 / 1024

        actual_checksum = self.helper._verify_checksum(
            output_path,
            display_name=output_path.name,
        )

        self.helper.ui.finish(
            str(output_path),
            size=size,
            elapsed=elapsed,
            avg_speed=avg_speed,
            source="Google Drive",
            checksum_label=(
                self.helper.checksum.label
                if self.helper.checksum is not None
                else None
            ),
            checksum_digest=actual_checksum,
        )
