import requests

url = "https://quickshare.samsungcloud.com/8nfsX2gdD4Uu"

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 16; SM-S911B) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/138.0.0.0 Mobile Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://quickshare.samsungcloud.com/",
}

session = requests.Session()

r = session.get(url, headers=headers, allow_redirects=True)

print("FINAL URL:", r.url)
print("STATUS:", r.status_code)
print("CONTENT TYPE:", r.headers.get("Content-Type"))
print("=" * 60)
print(r.text)
