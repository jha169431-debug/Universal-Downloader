import unittest

from downloaders.pixeldrain import PixelDrain


class PixelDrainTests(unittest.TestCase):
    def setUp(self):
        self.pixeldrain = PixelDrain()

    def test_supports_file_viewer(self):
        self.assertTrue(
            PixelDrain.supports(
                "https://pixeldrain.com/u/abc123"
            )
        )

    def test_supports_list_viewer(self):
        self.assertTrue(
            PixelDrain.supports(
                "https://pixeldrain.com/l/list123"
            )
        )

    def test_does_not_claim_unrelated_path(self):
        self.assertFalse(
            PixelDrain.supports(
                "https://pixeldrain.com/about"
            )
        )

    def test_parse_file_viewer(self):
        target = PixelDrain.parse_target(
            "https://pixeldrain.com/u/abc123"
        )

        self.assertEqual(target.kind, "file")
        self.assertEqual(target.ident, "abc123")

    def test_parse_list_viewer(self):
        target = PixelDrain.parse_target(
            "https://pixeldrain.com/l/list123"
        )

        self.assertEqual(target.kind, "list")
        self.assertEqual(target.ident, "list123")

    def test_parse_api_file_url(self):
        target = PixelDrain.parse_target(
            "https://pixeldrain.com/api/file/abc123?download"
        )

        self.assertEqual(target.kind, "file")
        self.assertEqual(target.ident, "abc123")

    def test_file_download_url(self):
        self.assertEqual(
            self.pixeldrain._file_download_url("abc123"),
            "https://pixeldrain.com/api/file/abc123?download",
        )

    def test_list_assets(self):
        payload = {
            "files": [
                {
                    "id": "one",
                    "name": "one.zip",
                    "size": 100,
                },
                {
                    "id": "two",
                    "name": "two.apk",
                    "size": 200,
                },
            ]
        }

        assets = self.pixeldrain._list_assets(payload)

        self.assertEqual(
            [asset["id"] for asset in assets],
            ["one", "two"],
        )
        self.assertEqual(
            [asset["name"] for asset in assets],
            ["one.zip", "two.apk"],
        )


if __name__ == "__main__":
    unittest.main()
