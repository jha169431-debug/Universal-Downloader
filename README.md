# 🌍 Universal Downloader

A lightweight terminal-based downloader written in Python.

Universal Downloader supports downloading files from multiple services through a clean terminal interface.

---

## ✨ Features

- ✅ Direct URL Downloads
- ✅ Google Drive Support
- ✅ MediaFire Support
- ✅ Samsung Quick Share Support
- ✅ GitHub Releases Support
- ✅ Live Progress Bar
- ✅ Human-readable Download Speed
- ✅ Human-readable ETA
- ✅ Automatic Filename Detection
- ✅ Resumable HTTP Downloads
- ✅ Safe `.part` Files Until Completion
- ✅ BUILD_DRIVE Auto-detection on Linux
- ✅ Automatic Retry + Exponential Backoff
- ✅ Mid-stream Network Recovery with HTTP Range
- ✅ Expired Direct-link Refresh
- ✅ Modular Architecture

---

## 📂 Project Structure

```
UniversalDownloader/
├── downloader.py
├── terminal_ui.py
├── requirements.txt
└── downloaders/
    ├── direct.py
    ├── gdrive.py
    ├── github.py
    ├── mediafire.py
    └── quickshare.py
```

---

## 🚀 Installation

Modern Debian/Ubuntu-based distributions protect the system Python environment (PEP 668), so install Universal Downloader inside a virtual environment.

```bash
git clone https://github.com/jha169431-debug/Universal-Downloader.git
cd Universal-Downloader

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

python downloader.py
```

## 🐙 GitHub Releases

Paste any of these directly into Universal Downloader:

```text
https://github.com/OWNER/REPO
https://github.com/OWNER/REPO/releases
https://github.com/OWNER/REPO/releases/latest
https://github.com/OWNER/REPO/releases/tag/v1.2.3
https://github.com/OWNER/REPO/releases/download/v1.2.3/file.zip
```

Repository and release-page URLs resolve through the GitHub Releases API. If a release has multiple uploaded assets, Universal Downloader shows an interactive asset picker with filenames and sizes. A direct `/releases/download/...` asset URL goes straight into the normal resumable download engine.

Public repositories work without authentication. If GitHub's anonymous API rate limit is reached, export a token before launching:

```bash
export GITHUB_TOKEN="your_token"
# or:
export GH_TOKEN="your_token"
```

If `python3 -m venv .venv` reports that venv support is missing:

```bash
sudo apt update
sudo apt install -y python3-venv
```

### Preview the terminal UI

The UI itself uses only Python's standard library, so the v4 preview can be tested without installing downloader dependencies:

```bash
git fetch origin
git switch main
python3 test_ui.py
```

---

## 🛣️ Roadmap

### v0.2
- ✅ Resume downloads
- ✅ Better terminal UI
- PixelDrain support
- ✅ GitHub Releases support

### v0.3
- ✅ Automatic retry / network recovery
- Multi-thread downloads
- Download queue
- SHA-256 verification
- Configuration file

---

## 📜 License

MIT License

---

Made with ❤️ by **NPL🇳🇵ROM™**
