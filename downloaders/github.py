import os
from urllib.parse import quote, unquote, urlparse

from downloaders.direct import DirectDownloader


class GitHubRelease:
    """Resolve GitHub repository/release URLs to downloadable assets."""

    API_ROOT = "https://api.github.com"

    def __init__(self):
        self.downloader = DirectDownloader(
            source_name="GitHub Releases"
        )
        self.ui = self.downloader.ui

    def _parse_github_url(self, url):
        parsed = urlparse(url)

        if parsed.netloc.lower() not in {
            "github.com",
            "www.github.com",
        }:
            raise ValueError("Not a GitHub URL.")

        raw_parts = [
            part
            for part in parsed.path.split("/")
            if part
        ]

        if len(raw_parts) < 2:
            raise ValueError(
                "GitHub URL must include owner/repository."
            )

        owner = unquote(raw_parts[0])
        repo = unquote(raw_parts[1])

        if repo.endswith(".git"):
            repo = repo[:-4]

        # Direct release asset:
        # /owner/repo/releases/download/<tag>/<filename>
        if (
            len(raw_parts) >= 6
            and raw_parts[2] == "releases"
            and raw_parts[3] == "download"
        ):
            return {
                "owner": owner,
                "repo": repo,
                "kind": "asset",
                "tag": unquote(raw_parts[4]),
                "asset_url": url,
            }

        # GitHub also supports a stable latest-release asset form:
        # /owner/repo/releases/latest/download/<filename>
        if (
            len(raw_parts) >= 6
            and raw_parts[2] == "releases"
            and raw_parts[3] == "latest"
            and raw_parts[4] == "download"
        ):
            return {
                "owner": owner,
                "repo": repo,
                "kind": "asset",
                "tag": "latest",
                "asset_url": url,
            }

        # Tagged release:
        # /owner/repo/releases/tag/<tag>
        if (
            len(raw_parts) >= 5
            and raw_parts[2] == "releases"
            and raw_parts[3] == "tag"
        ):
            tag = unquote("/".join(raw_parts[4:]))

            return {
                "owner": owner,
                "repo": repo,
                "kind": "tag",
                "tag": tag,
            }

        # /releases/latest, /releases, and bare repository URLs all resolve
        # to the latest published release.
        return {
            "owner": owner,
            "repo": repo,
            "kind": "latest",
            "tag": None,
        }

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

    def _fetch_release(self, owner, repo, tag=None):
        safe_owner = quote(owner, safe="")
        safe_repo = quote(repo, safe="")

        if tag is None:
            endpoint = (
                f"{self.API_ROOT}/repos/"
                f"{safe_owner}/{safe_repo}/releases/latest"
            )
        else:
            safe_tag = quote(tag, safe="")
            endpoint = (
                f"{self.API_ROOT}/repos/"
                f"{safe_owner}/{safe_repo}/releases/tags/"
                f"{safe_tag}"
            )

        self.ui.start(
            "Reading GitHub release metadata…"
        )

        response = self.downloader._request(
            endpoint,
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
                if tag is not None:
                    message = (
                        f"GitHub release tag not found: {tag}"
                    )
                else:
                    message = (
                        "GitHub repository has no latest "
                        "published release."
                    )

                raise RuntimeError(message)

            response.raise_for_status()
            return response.json()
        finally:
            response.close()

    def _release_assets(self, release):
        assets = []

        for asset in release.get("assets", []):
            url = asset.get("browser_download_url")

            if not url:
                continue

            assets.append(
                {
                    "name": asset.get(
                        "name",
                        "unnamed-asset",
                    ),
                    "size": int(
                        asset.get("size", 0) or 0
                    ),
                    "url": url,
                    "content_type": asset.get(
                        "content_type",
                        "",
                    ),
                }
            )

        return assets

    def _choose_asset(self, release, assets):
        if not assets:
            raise RuntimeError(
                "This GitHub release has no uploaded assets."
            )

        if len(assets) == 1:
            return assets[0]

        release_name = (
            release.get("name")
            or release.get("tag_name")
            or "GitHub Release"
        )
        tag = release.get("tag_name") or ""

        return self.ui.choose_asset(
            release_name,
            tag,
            assets,
        )

    def download(self, url):
        info = self._parse_github_url(url)

        # A direct /releases/download/... URL is already the asset.
        if info["kind"] == "asset":
            self.downloader.download(
                info["asset_url"]
            )
            return

        release = self._fetch_release(
            info["owner"],
            info["repo"],
            tag=info["tag"],
        )

        assets = self._release_assets(release)
        asset = self._choose_asset(
            release,
            assets,
        )

        self.ui.update(
            f"Selected GitHub asset: {asset['name']}"
        )

        self.downloader.download(
            asset["url"]
        )
