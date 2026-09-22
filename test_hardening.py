import io
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import downloader
import terminal_ui
from downloaders.direct import DirectDownloader


class FilenameSafetyTests(unittest.TestCase):
    def setUp(self):
        self.downloader = DirectDownloader()

    @staticmethod
    def response(content_disposition="", url="https://example.com/file.zip"):
        return SimpleNamespace(
            headers={
                "Content-Disposition": content_disposition,
            },
            url=url,
        )

    def test_strips_posix_path_traversal(self):
        response = self.response(
            'attachment; filename="../../outside.zip"'
        )

        self.assertEqual(
            self.downloader._filename(
                response,
                response.url,
            ),
            "outside.zip",
        )

    def test_strips_windows_path_traversal(self):
        response = self.response(
            'attachment; filename="..\\..\\outside.zip"'
        )

        self.assertEqual(
            self.downloader._filename(
                response,
                response.url,
            ),
            "outside.zip",
        )

    def test_sanitizes_rfc5987_filename(self):
        response = self.response(
            "attachment; filename*=UTF-8''..%2F..%2From.zip"
        )

        self.assertEqual(
            self.downloader._filename(
                response,
                response.url,
            ),
            "rom.zip",
        )

    def test_removes_control_characters(self):
        self.assertEqual(
            self.downloader._sanitize_filename(
                "rom\x00build\n.zip"
            ),
            "rom_build_.zip",
        )

    def test_empty_or_dot_name_falls_back(self):
        self.assertEqual(
            self.downloader._sanitize_filename(".."),
            "download",
        )

    def test_long_name_keeps_archive_suffix(self):
        safe = self.downloader._sanitize_filename(
            ("a" * 300) + ".tar.gz"
        )

        self.assertLessEqual(len(safe), 240)
        self.assertTrue(safe.endswith(".tar.gz"))




class TerminalPanelTests(unittest.TestCase):
    def test_error_panel_finishes_with_newline(self):
        ui = terminal_ui.TerminalUI()
        ui._interactive = True
        ui._color = False
        ui._render = MagicMock()
        ui._show_cursor = MagicMock()
        stream = io.StringIO()

        with patch.object(terminal_ui.sys, "stdout", stream):
            ui.error("boom")

        self.assertEqual(stream.getvalue(), "\n")

    def test_cancelled_panel_finishes_with_newline(self):
        ui = terminal_ui.TerminalUI()
        ui._interactive = True
        ui._color = False
        ui._render = MagicMock()
        ui._show_cursor = MagicMock()
        stream = io.StringIO()

        with patch.object(terminal_ui.sys, "stdout", stream):
            ui.cancelled()

        self.assertEqual(stream.getvalue(), "\n")


class ExitCodeTests(unittest.TestCase):
    @patch("downloader.TerminalUI")
    @patch("builtins.input", return_value="")
    def test_empty_url_returns_failure(
        self,
        _input,
        terminal_ui,
    ):
        terminal_ui.return_value = MagicMock()

        self.assertEqual(downloader.main(), 1)

    @patch("downloader.TerminalUI")
    @patch("builtins.input", return_value="https://example.com/file.zip")
    @patch("downloader.detect_source")
    def test_success_returns_zero(
        self,
        detect_source,
        _input,
        terminal_ui,
    ):
        class SuccessDownloader:
            def download(self, _url):
                return None

        detect_source.return_value = (
            "Direct URL",
            SuccessDownloader,
        )
        terminal_ui.return_value = MagicMock()

        self.assertEqual(downloader.main(), 0)

    @patch("downloader.TerminalUI")
    @patch("builtins.input", return_value="https://example.com/file.zip")
    @patch("downloader.detect_source")
    def test_runtime_failure_returns_one(
        self,
        detect_source,
        _input,
        terminal_ui,
    ):
        class FailingDownloader:
            def download(self, _url):
                raise RuntimeError("boom")

        detect_source.return_value = (
            "Direct URL",
            FailingDownloader,
        )
        terminal_ui.return_value = MagicMock()

        self.assertEqual(downloader.main(), 1)

    @patch("downloader.TerminalUI")
    @patch("builtins.input", return_value="https://example.com/file.zip")
    @patch("downloader.detect_source")
    def test_keyboard_interrupt_returns_130(
        self,
        detect_source,
        _input,
        terminal_ui,
    ):
        class CancelledDownloader:
            def download(self, _url):
                raise KeyboardInterrupt

        detect_source.return_value = (
            "Direct URL",
            CancelledDownloader,
        )
        terminal_ui.return_value = MagicMock()

        self.assertEqual(downloader.main(), 130)


if __name__ == "__main__":
    unittest.main()
