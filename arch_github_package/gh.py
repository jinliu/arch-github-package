import urllib.request
from pathlib import Path

import typer
from github import Github

_github = Github()


class Releases:
    def __init__(self, repo: str):
        self.repo_name = repo
        self.repo = _github.get_repo(repo)
        self.releases = self.repo.get_releases()
        if self.releases.totalCount == 0:
            raise ValueError("No releases found")

    def get_repo_name(self):
        return self.repo_name

    def get_project_name(self):
        return self.repo.name

    def get_project_description(self):
        return self.repo.description

    def get_latest_version(self):
        r = self.releases[0]
        ver = r.tag_name.replace("-", "_")
        if ver.startswith("v"):
            ver = ver[1:]
        return ver

    def get_publish_date(self):
        r = self.releases[0]
        return r.published_at.strftime("%Y-%m-%d")
    
    def download_tarball(self, save_dir):
        assets = self.releases[0].assets
        asset_scoretable = []
        arch = ["linux", "amd64", "x86_64", "x86-64", "x64"]
        lib = ["glibc", "gnu"]
        extensions = ["tar", "tgz", "gz", "zip"]
        for asset in assets:
            score = 0
            s = asset.name.lower()
            for kw in arch:
                if kw in s:
                    score += 100
            if any(f".{ext}" in s for ext in extensions):
                score += 10
            for kw in arch:
                if kw in s:
                    score += 1            
            asset_scoretable.append((asset, score))
        asset_scoretable.sort(key=lambda x: x[1], reverse=True)

        if len(asset_scoretable) == 0:
            raise ValueError("No tarballs found")

        print(f"Found {len(asset_scoretable)} tarballs:\n")
        for i, (asset, score) in enumerate(asset_scoretable):
            print(f"{i}. {asset.name}")
        asset = asset_scoretable[typer.prompt("\nSelect tarball to download", type=int, default=0)][0]

        with typer.progressbar(label="Downloading", length=asset.size) as progress:
            def report(blocknum, blocksize, totalsize):
                progress.update(blocknum * blocksize - progress.pos)
            urllib.request.urlretrieve(asset.browser_download_url, Path(save_dir)/asset.name, reporthook=report)
        
        return asset.name
