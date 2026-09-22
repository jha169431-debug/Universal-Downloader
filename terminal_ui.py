import os
import shutil
import sys
import time


class TerminalUI:
    """Small, dependency-free terminal UI for Universal Downloader."""

    VERSION = "4.4"

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"
    GREEN = "\033[92m"
    RED = "\033[91m"

    def __init__(self, refresh_interval=0.08):
        self.first_draw = True
        self.refresh_interval = refresh_interval
        self._last_draw = 0.0
        self._spinner_index = 0
        self._interactive = (
            sys.stdout.isatty()
            and os.environ.get("TERM", "") != "dumb"
        )
        self._color = (
            self._interactive
            and "NO_COLOR" not in os.environ
        )

    def _ansi(self, code, text):
        if not self._color:
            return text
        return f"{code}{text}{self.RESET}"

    def clear(self):
        if self._interactive:
            sys.stdout.write("\033[2J\033[H")
            sys.stdout.flush()
        else:
            print()

    def _terminal_width(self):
        columns = shutil.get_terminal_size(fallback=(80, 24)).columns
        return min(max(columns - 2, 20), 72)

    def _truncate(self, text, length):
        text = str(text)

        if len(text) <= length:
            return text

        if length <= 8:
            return text[: max(1, length - 1)] + "…"

        left = (length - 1) // 2
        right = length - left - 1
        return f"{text[:left]}…{text[-right:]}"

    def _format_size(self, size):
        units = ["B", "KB", "MB", "GB", "TB"]
        value = max(0.0, float(size or 0))

        for unit in units:
            if value < 1024 or unit == units[-1]:
                if unit == "B":
                    return f"{int(value)} {unit}"
                return f"{value:.2f} {unit}"
            value /= 1024

    def _format_speed(self, speed):
        # speed is provided in MB/s by DirectDownloader
        speed = max(0.0, float(speed or 0))

        if speed >= 1024:
            return f"{speed / 1024:.2f} GB/s"
        if speed >= 1:
            return f"{speed:.2f} MB/s"
        return f"{speed * 1024:.0f} KB/s"

    def _format_eta(self, seconds):
        seconds = max(0, int(seconds or 0))

        if seconds < 60:
            return f"00:{seconds:02d}"

        minutes, seconds = divmod(seconds, 60)

        if minutes < 60:
            return f"{minutes:02d}:{seconds:02d}"

        hours, minutes = divmod(minutes, 60)

        if hours < 24:
            return f"{hours:02d}h {minutes:02d}m"

        days, hours = divmod(hours, 24)
        return f"{days}d {hours:02d}h"

    def _border(self, width, left="╭", fill="─", right="╮"):
        return left + (fill * max(0, width - 2)) + right

    def _box_line(self, text, width, align="left"):
        inner = max(1, width - 4)
        text = self._truncate(text, inner)

        if align == "center":
            body = text.center(inner)
        else:
            body = text.ljust(inner)

        return f"│ {body} │"

    def _progress_bar(self, percent, width):
        """
        Ball-only progress bar with a caterpillar made from round beads.

        Filled progress uses solid balls, remaining progress uses hollow
        balls, and the animated bead cluster appears once enough progress
        exists for it to crawl naturally.
        """
        width = max(6, width)
        percent = max(0.0, min(percent, 100.0))

        progress = width * percent / 100.0
        full = int(progress)

        # Ball-only base: no block characters at all.
        cells = [
            "●" if index < full else "○"
            for index in range(width)
        ]

        # Show a small leading bead for fractional progress so the bar still
        # feels smooth even before the next whole cell is completed.
        fraction = progress - full
        if (
            0 < fraction
            and full < width
            and percent < 100
        ):
            cells[full] = "◌"

        # Let the real progress establish itself first. Once six completed
        # cells exist, a 5-bead caterpillar starts crawling through them.
        if 0 < percent < 100 and full >= 6:
            tick = int(time.monotonic() * 10)

            poses = (
                ("◉", "●", "●", "●", "●"),
                ("●", "◉", "●", "●", "●"),
                ("●", "●", "◉", "●", "●"),
                ("●", "●", "●", "◉", "●"),
                ("●", "●", "●", "●", "◉"),
            )
            pose = poses[tick % len(poses)]

            travel = full + len(pose)
            start = (
                (tick // 2) % travel
            ) - len(pose)

            for offset, glyph in enumerate(pose):
                index = start + offset

                if 0 <= index < full:
                    cells[index] = glyph

        return "".join(cells)

    def _render(self, lines):
        output = "\n".join(lines)

        if self._interactive:
            if self.first_draw:
                prefix = "\033[2J\033[H"
                self.first_draw = False
            else:
                # Repaint in place instead of clearing the whole screen.
                prefix = "\033[H"

            sys.stdout.write(prefix + output + "\033[J")
            sys.stdout.flush()
            return

        print(output, flush=True)

    def _brand_lines(self, width):
        title = self._box_line("UNIVERSAL DOWNLOADER", width, "center")
        brand = self._box_line(
            f"NPL ROM  •  UI v{self.VERSION}",
            width,
            "center",
        )

        return [
            self._ansi(self.BOLD, title),
            self._ansi(self.MAGENTA, brand),
        ]

    def _status_panel(self, message, state="active"):
        width = self._terminal_width()
        spinner = ("◐", "◓", "◑", "◒")[
            self._spinner_index % 4
        ]
        self._spinner_index += 1

        if state == "done":
            status = f"✓ READY  {message}"
            status_line = self._ansi(
                self.GREEN,
                self._box_line(status, width),
            )
        elif state == "error":
            status = f"! FAILED  {message}"
            status_line = self._ansi(
                self.RED,
                self._box_line(status, width),
            )
        else:
            status = f"{spinner} WORKING  {message}"
            status_line = self._ansi(
                self.CYAN,
                self._box_line(status, width),
            )

        title, brand = self._brand_lines(width)

        lines = [
            self._border(width),
            title,
            brand,
            self._border(width, "├", "─", "┤"),
            status_line,
            self._border(width, "╰", "─", "╯"),
        ]

        self._render(lines)

    # Compatibility helpers used by test_ui.py and useful for URL resolution.
    def start(self, message="Connecting…"):
        self.first_draw = True
        self._status_panel(message, "active")

    def update(self, message):
        self._status_panel(message, "active")

    def stop(self, message="Ready!"):
        self._status_panel(message, "done")

    def draw(self, filename, downloaded, total, speed, eta):
        now = time.monotonic()
        complete = total > 0 and downloaded >= total

        # A fast connection can call draw hundreds of times per second.
        # ~12 FPS is visually smooth while keeping terminal overhead tiny.
        interval = self.refresh_interval if self._interactive else 1.0
        if (
            not complete
            and now - self._last_draw < interval
        ):
            return

        self._last_draw = now
        width = self._terminal_width()
        inner = max(1, width - 4)

        known_total = total > 0

        if known_total:
            percent = min(downloaded * 100 / total, 100.0)
            percent_text = f"{percent:5.1f}%"
        else:
            percent = 0.0
            percent_text = "  --.-%"

        bar_width = max(
            6,
            inner - len(percent_text) - 1,
        )

        if known_total:
            bar = self._progress_bar(percent, bar_width)
        else:
            spinner = ("◐", "◓", "◑", "◒")[
                self._spinner_index % 4
            ]
            self._spinner_index += 1
            bar = (
                f"{spinner} "
                + ("░" * max(0, bar_width - 2))
            )

        size_text = (
            self._format_size(total)
            if known_total
            else "Unknown"
        )
        downloaded_text = self._format_size(downloaded)
        total_text = (
            self._format_size(total)
            if known_total
            else "?"
        )
        filename_text = self._truncate(
            filename,
            max(8, inner - 6),
        )

        status_text = (
            "✓ DOWNLOAD COMPLETE"
            if complete
            else "● DOWNLOAD ACTIVE"
        )
        status_color = (
            self.GREEN if complete else self.CYAN
        )

        title, brand = self._brand_lines(width)
        status_line = self._ansi(
            status_color,
            self._box_line(status_text, width),
        )

        lines = [
            self._border(width),
            title,
            brand,
            self._border(width, "├", "─", "┤"),
            status_line,
            self._box_line(
                f"File  {filename_text}",
                width,
            ),
            self._box_line(
                f"Size  {size_text}",
                width,
            ),
            self._box_line("", width),
            self._box_line(
                f"{bar} {percent_text}",
                width,
            ),
            self._box_line("", width),
            self._box_line(
                f"↓  {downloaded_text} / {total_text}",
                width,
            ),
            self._box_line(
                f"⚡ {self._format_speed(speed)}",
                width,
            ),
            self._box_line(
                f"⏱  {self._format_eta(eta)} remaining",
                width,
            ),
            self._border(width, "├", "─", "┤"),
            self._box_line("Ctrl+C  Cancel", width),
            self._border(width, "╰", "─", "╯"),
        ]

        self._render(lines)

    def finish(self, filename):
        width = self._terminal_width()
        inner = max(1, width - 4)
        saved_as = self._truncate(
            filename,
            max(8, inner - 10),
        )

        title = self._ansi(
            self.GREEN,
            self._box_line(
                "✓ DOWNLOAD COMPLETE",
                width,
                "center",
            ),
        )

        lines = [
            self._border(width),
            title,
            self._border(width, "├", "─", "┤"),
            self._box_line(
                f"Saved as  {saved_as}",
                width,
            ),
            self._box_line(
                "Download finished successfully.",
                width,
            ),
            self._border(width, "╰", "─", "╯"),
        ]

        self._render(lines)

        if self._interactive:
            sys.stdout.write("\n")
            sys.stdout.flush()
