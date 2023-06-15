from github import Github
import urllib.request
from pathlib import Path


_github = Github()


class Releases:
    def __init__(self, repo: str):
        self.repo_name = repo
        self.repo = _github.get_repo(repo)
        self.releases = self.repo.get_releases()

    def get_repo_name(self):
        return self.repo_name

    def get_project_name(self):
        return self.repo.name

    def get_project_description(self):
        return self.repo.description

    def get_latest_version(self):
        r = self.releases[0]
        ver = r.tag_name.replace('-', '_')
        if ver.startswith('v'):
            ver = ver[1:]
        return ver

    def get_publish_date(self):
        r = self.releases[0]
        return r.published_at.strftime('%Y%m%d')
    
    def download_tarball(self, save_dir):
        assets = self.releases[0].assets
        for asset in assets:
            if any(asset.name.endswith(f'{i}.{j}') for i in ["Linux_x86_64", "linux_amd64", "linux64", "linux-glibc-x86_64"] for j in ["tar.gz", "tgz", "zip"]):
                urllib.request.urlretrieve(asset.browser_download_url, Path(save_dir)/asset.name)
                return asset.name
        raise Exception("No tarball found")

if __name__ == "__main__":
    r = Releases("zix99/rare")
    print(r.get_project_name())
    print(r.get_project_description())
    print(r.get_latest_version())
    print(r.get_publish_date())
    print(r.download_tarball("/tmp"))
