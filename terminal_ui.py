import os
import sys


class TerminalUI:
    VERSION = "3.1"

    def __init__(self):
        self.first_draw = True

    def clear(self):
        os.system("clear")

    def _truncate(self, text, length=40):
        if len(text) <= length:
            return text

        return text[:22] + "..." + text[-15:]

    def _format_size(self, size):
        units = ["B", "KB", "MB", "GB", "TB"]

        value = float(size)

        for unit in units:
            if value < 1024 or unit == units[-1]:
                if unit == "B":
                    return f"{int(value)} {unit}"
                return f"{value:.2f} {unit}"
            value /= 1024

    def _format_speed(self, speed):
        # speed comes in MB/s
        if speed >= 1024:
            return f"{speed / 1024:.2f} GB/s"
        elif speed >= 1:
            return f"{speed:.2f} MB/s"
        else:
            return f"{speed * 1024:.0f} KB/s"

    def _format_eta(self, seconds):
        seconds = int(seconds)

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

    def draw(self, filename, downloaded, total, speed, eta):
        if self.first_draw:
            self.clear()
            self.first_draw = False

        percent = 0 if total == 0 else downloaded * 100 / total

        width = 38
        filled = int(width * percent / 100)

        if filled >= width:
            bar = "█" * width
        else:
            bar = (
                "█" * filled +
                "▶" +
                "─" * (width - filled - 1)
            )

        sys.stdout.write("\033[H\033[J")

        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print()
        print("          Universal Downloader")
        print("             by NPL🇳🇵ROM™")
        print(f"                  v{self.VERSION}")
        print()
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print()

        print(f"📦 File       : {self._truncate(filename)}")
        print(f"📏 Size       : {self._format_size(total)}")
        print()

        print(f"{bar} {percent:6.2f}%")
        print()

        print(
            f"⬇ Downloaded : {self._format_size(downloaded)} / "
            f"{self._format_size(total)}"
        )

        print(f"⚡ Speed      : {self._format_speed(speed)}")
        print(f"⏱ ETA        : {self._format_eta(eta)}")

        print()
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        sys.stdout.flush()

    def finish(self, filename):
        print()
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print()
        print("✅ Download Complete")
        print()
        print(f"📂 Saved as : {filename}")
        print()
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

