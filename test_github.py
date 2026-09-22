import unittest

from downloaders.github import GitHubRelease


class GitHubReleaseTests(unittest.TestCase):
    def setUp(self):
        self.github = GitHubRelease()

    def test_bare_repo_resolves_latest(self):
        info = self.github._parse_github_url(
            "https://github.com/owner/project"
        )

        self.assertEqual(info["owner"], "owner")
        self.assertEqual(info["repo"], "project")
        self.assertEqual(info["kind"], "latest")
        self.assertIsNone(info["tag"])

    def test_latest_release_url(self):
        info = self.github._parse_github_url(
            "https://github.com/owner/project/releases/latest"
        )

        self.assertEqual(info["kind"], "latest")

    def test_tagged_release_url(self):
        info = self.github._parse_github_url(
            "https://github.com/owner/project/releases/tag/v1.2.3"
        )

        self.assertEqual(info["kind"], "tag")
        self.assertEqual(info["tag"], "v1.2.3")

    def test_direct_release_asset_url(self):
        url = (
            "https://github.com/owner/project/releases/"
            "download/v1.2.3/app.zip"
        )
        info = self.github._parse_github_url(url)

        self.assertEqual(info["kind"], "asset")
        self.assertEqual(info["asset_url"], url)

    def test_release_assets_excludes_missing_urls(self):
        release = {
            "assets": [
                {
                    "name": "app.zip",
                    "size": 123,
                    "browser_download_url": (
                        "https://github.com/owner/project/"
                        "releases/download/v1/app.zip"
                    ),
                },
                {
                    "name": "broken",
                    "size": 0,
                    "browser_download_url": None,
                },
            ]
        }

        assets = self.github._release_assets(release)

        self.assertEqual(len(assets), 1)
        self.assertEqual(assets[0]["name"], "app.zip")


if __name__ == "__main__":
    unittest.main()
