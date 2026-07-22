import os
import gdown


class GoogleDrive:

    def download(self, url):

        output = gdown.download(
            url=url,
            output=None,
            quiet=False,
            fuzzy=True
        )

        if output and os.path.exists(output):
            print(f"\n✓ Download Complete")
            print(f"Saved as: {output}")
        else:
            raise Exception("Download failed.")
