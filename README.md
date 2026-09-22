# 🌍 Universal Downloader

A lightweight terminal-based downloader written in Python.

Universal Downloader supports downloading files from multiple services through a clean terminal interface.

---

## ✨ Features

- ✅ Direct URL Downloads
- ✅ Google Drive Support
- ✅ MediaFire Support
- ✅ Samsung Quick Share Support
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
- ✅ SHA-256 Verification
- ✅ SHA-1 / MD5 Compatibility Verification
- ✅ Corrupt-file Quarantine
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

### Checksum verification

SHA-256 is the recommended verification path:

```bash
python downloader.py "https://example.com/file.zip" \
  --sha256 <expected-sha256>
```

The URL can still be entered interactively:

```bash
python downloader.py --sha256 <expected-sha256>
```

SHA-1 and MD5 are also accepted for compatibility with older release pages:

```bash
python downloader.py <url> --sha1 <expected-sha1>
python downloader.py <url> --md5 <expected-md5>
```

When a checksum is supplied, Universal Downloader verifies the completed bytes **before** a direct/MediaFire/Quick Share `.part` file is promoted to its final filename. A mismatch is quarantined as `*.corrupt` instead of being presented as a valid download.


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
- GitHub Releases support

### v0.3
- ✅ Automatic retry / network recovery
- ✅ SHA-256 verification
- Multi-thread downloads
- Download queue
- Configuration file

---

## 📜 License

MIT License

---

Made with ❤️ by **NPL🇳🇵ROM™**
