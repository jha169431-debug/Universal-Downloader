import os
import gdown


class GoogleDrive:

    def download(self, url):

        output = gdown.download(url, quiet=False)

        if output and os.path.exists(output):
            print("\n✓ Download Complete")
            print(f"Saved as: {output}")
        else:
            raise Exception("Download failed.")
