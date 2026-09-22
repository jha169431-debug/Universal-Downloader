import os
from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote, unquote, urlparse

from downloaders.direct import DirectDownloader


@dataclass(frozen=True)
class GitHubTarget:
    owner: str
    repo: str
    tag: Optional[str] = None
    direct_asset: bool = False


class GitHubRelease:
    API_ROOT = "https://api.github.com"

    def __init__(self):
        self.downloader = DirectDownloader(
            source_name="GitHub Releases"
        )
        self.ui = self.downloader.ui

    @staticmethod
    def supports(url):
        try:
            parsed = urlparse(url)
        except ValueError:
            return False

        if parsed.netloc.lower() not in {
            "github.com",
            "www.github.com",
        }:
            return False

        parts = [
            unquote(part)
            for part in parsed.path.split("/")
            if part
        ]

        if len(parts) < 2:
            return False

        if len(parts) == 2:
            return True

        return parts[2].lower() == "releases"

    @staticmethod
    def parse_target(url):
        parsed = urlparse(url)

        if parsed.netloc.lower() not in {
            "github.com",
            "www.github.com",
        }:
            raise ValueError(
                "GitHub release URLs must use github.com."
            )

        parts = [
            unquote(part)
            for part in parsed.path.split("/")
            if part
        ]

        if len(parts) < 2:
            raise ValueError(
                "GitHub URL must include owner and repository."
            )

        owner = parts[0]
        repo = parts[1]

        if repo.endswith(".git"):
            repo = repo[:-4]

        if not owner or not repo:
            raise ValueError(
                "GitHub URL must include owner and repository."
            )

        if len(parts) == 2:
            return GitHubTarget(owner, repo)

        if parts[2].lower() != "releases":
            raise ValueError(
                "Paste a repository or GitHub Releases URL."
            )

        if len(parts) >= 4 and parts[3].lower() == "download":
            return GitHubTarget(
                owner,
                repo,
                direct_asset=True,
            )

        if len(parts) >= 5 and parts[3].lower() == "tag":
            return GitHubTarget(
                owner,
                repo,
                tag="/".join(parts[4:]),
            )

        return GitHubTarget(owner, repo)

    def _api_headers(self):
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        token = (
            os.environ.get("GITHUB_TOKEN")
            or os.environ.get("GH_TOKEN")
        )

        if token:
            headers["Authorization"] = f"Bearer {token}"

        return headers

    def _release_url(self, target):
        repo_path = (
            f"{quote(target.owner, safe='')}/"
            f"{quote(target.repo, safe='')}"
        )

        if target.tag:
            encoded_tag = quote(target.tag, safe="")
            return (
                f"{self.API_ROOT}/repos/{repo_path}/"
                f"releases/tags/{encoded_tag}"
            )

        return (
            f"{self.API_ROOT}/repos/{repo_path}/"
            "releases/latest"
        )

    def _get_release(self, target):
        self.ui.start("Reading GitHub release…")

        response = self.downloader._request(
            self._release_url(target),
            stream=False,
            headers=self._api_headers(),
        )

        try:
            if (
                response.status_code == 403
                and response.headers.get(
                    "X-RateLimit-Remaining"
                ) == "0"
            ):
                raise RuntimeError(
                    "GitHub API rate limit reached. "
                    "Set GITHUB_TOKEN or GH_TOKEN and retry."
                )

            if response.status_code == 404:
                if target.tag:
                    raise RuntimeError(
                        f"GitHub release tag not found: "
                        f"{target.tag}"
                    )

                raise RuntimeError(
                    "No published GitHub release was found "
                    "for this repository."
                )

            response.raise_for_status()
            return response.json()
        finally:
            response.close()

    @staticmethod
    def _asset_priority(asset):
        name = asset.get("name", "").lower()

        metadata_suffixes = (
            ".sha256",
            ".sha256sum",
            ".sha1",
            ".md5",
            ".sig",
            ".asc",
            ".txt",
        )

        if name.endswith(metadata_suffixes):
            return 2

        preferred_suffixes = (
            ".zip",
            ".7z",
            ".apk",
            ".img",
            ".iso",
            ".tar.gz",
            ".tgz",
            ".xz",
            ".zst",
            ".exe",
            ".msi",
            ".deb",
            ".rpm",
        )

        if name.endswith(preferred_suffixes):
            return 0

        return 1

    def _release_assets(self, release):
        assets = [
            asset
            for asset in release.get("assets", [])
            if asset.get("state") == "uploaded"
            and asset.get("browser_download_url")
        ]

        return sorted(
            assets,
            key=lambda asset: (
                self._asset_priority(asset),
                asset.get("name", "").lower(),
            ),
        )

    def _select_asset(self, release, assets):
        if len(assets) == 1:
            return assets[0]

        release_name = (
            release.get("name")
            or release.get("tag_name")
            or "GitHub Release"
        )

        return self.ui.choose_asset(
            release_name,
            assets,
        )

    def download(self, url):
        target = self.parse_target(url)

        if target.direct_asset:
            self.downloader.download(url)
            return

        release = self._get_release(target)
        assets = self._release_assets(release)

        if not assets:
            raise RuntimeError(
                "This GitHub release has no downloadable assets."
            )

        asset = self._select_asset(release, assets)

        self.ui.update(
            f"Selected {asset.get('name', 'release asset')}"
        )

        self.downloader.download(
            asset["browser_download_url"]
        )
