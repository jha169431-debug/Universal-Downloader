import unittest

from downloaders.github import GitHubRelease


class GitHubReleaseTests(unittest.TestCase):
    def test_supports_repo_url(self):
        self.assertTrue(
            GitHubRelease.supports(
                "https://github.com/owner/repo"
            )
        )

    def test_does_not_claim_blob_url(self):
        self.assertFalse(
            GitHubRelease.supports(
                "https://github.com/owner/repo/blob/main/file.zip"
            )
        )

    def test_parse_tagged_release(self):
        target = GitHubRelease.parse_target(
            "https://github.com/owner/repo/releases/tag/v1.2.3"
        )
        self.assertEqual(target.owner, "owner")
        self.assertEqual(target.repo, "repo")
        self.assertEqual(target.tag, "v1.2.3")
        self.assertFalse(target.direct_asset)

    def test_parse_direct_asset(self):
        target = GitHubRelease.parse_target(
            "https://github.com/owner/repo/releases/download/v1/app.apk"
        )
        self.assertTrue(target.direct_asset)

    def test_latest_release_api_url(self):
        obj = GitHubRelease.__new__(GitHubRelease)
        target = GitHubRelease.parse_target(
            "https://github.com/owner/repo/releases/latest"
        )
        self.assertEqual(
            obj._release_url(target),
            "https://api.github.com/repos/owner/repo/releases/latest",
        )

    def test_tag_slash_is_encoded(self):
        obj = GitHubRelease.__new__(GitHubRelease)
        target = GitHubRelease.parse_target(
            "https://github.com/owner/repo/releases/tag/release/2026"
        )
        self.assertTrue(
            obj._release_url(target).endswith(
                "/releases/tags/release%2F2026"
            )
        )

    def test_assets_prefer_binary_over_hash(self):
        obj = GitHubRelease.__new__(GitHubRelease)
        release = {
            "assets": [
                {
                    "name": "tool.sha256",
                    "state": "uploaded",
                    "browser_download_url": "https://example/hash",
                },
                {
                    "name": "tool.zip",
                    "state": "uploaded",
                    "browser_download_url": "https://example/zip",
                },
            ]
        }
        assets = obj._release_assets(release)
        self.assertEqual(assets[0]["name"], "tool.zip")


if __name__ == "__main__":
    unittest.main()
