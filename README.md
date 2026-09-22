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
- ✅ PixelDrain File + List Support
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
    ├── pixeldrain.py
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

If `python3 -m venv .venv` reports that venv support is missing:

```bash
sudo apt update
sudo apt install -y python3-venv
```

### GitHub Releases

Paste a repository, release page, tagged release, or direct release asset URL. Repository/release pages resolve through the GitHub Releases API and multiple assets are shown in an in-terminal picker. Binary packages are listed ahead of checksum/signature metadata.

Public repositories work without authentication. If GitHub API rate limits are reached, set `GITHUB_TOKEN` or `GH_TOKEN` before launching the downloader.

### PixelDrain

Paste a normal PixelDrain file link, list link, or API file link:

```text
https://pixeldrain.com/u/FILE_ID
https://pixeldrain.com/l/LIST_ID
https://pixeldrain.com/api/file/FILE_ID?download
```

Single files are handed to the normal resumable engine. PixelDrain lists are resolved through the public API and shown in the existing terminal picker before download. Resume and automatic network recovery are inherited from `DirectDownloader`.

PixelDrain can require a browser captcha or enforce free-account transfer/concurrency limits. When the API reports one of those restrictions, Universal Downloader keeps the partial file and shows a readable error instead of treating the API response as a download.

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
- ✅ PixelDrain support
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
