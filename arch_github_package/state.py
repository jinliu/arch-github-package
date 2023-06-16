import configparser
import fcntl
import os
from pathlib import Path


class Package:
    @staticmethod
    def load(state_dir, package_name):
        config = configparser.ConfigParser()
        config.read(Path(state_dir)/package_name)
        c = config["DEFAULT"]
        return Package(state_dir, package_name, c["repo"], c["version"], c["publish_date"])
        
    def __init__(self, state_dir, package_name, repo, version, publish_date):
        self.state_dir = state_dir
        self.package_name = package_name
        self.repo = repo
        self.version = version
        self.publish_date = publish_date

    def save(self):
        config = configparser.ConfigParser()
        c = config["DEFAULT"]
        c["repo"] = self.repo
        c["version"] = self.version
        c["publish_date"] = self.publish_date
        with open(self.state_dir/self.package_name, "w") as f:
            config.write(f)

    def remove(self):
        (self.state_dir/self.package_name).unlink()


class State:
    def __init__(self):
        self.state_dir = Path.home()/".local/share/arch-github-package"
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def __enter__(self):
        self.state_dir_fd = os.open(self.state_dir, os.O_RDONLY)
        fcntl.flock(self.state_dir_fd, fcntl.LOCK_EX)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        fcntl.flock(self.state_dir_fd, fcntl.LOCK_UN)
        os.close(self.state_dir_fd)

    def list_packages(self):
        return sorted((Package.load(self.state_dir, f.name) for f in self.state_dir.iterdir()),
                      key=lambda p: p.package_name)

    def get_package(self, package_name):
        packages = self.list_packages()
        for i in packages:
            if i.package_name == package_name or i.repo == package_name:
                return i
        raise ValueError(f"Package {package_name} does not exist")

    def new_package(self, package_name, repo, version, publish_date):
        Package(self.state_dir, package_name, repo, version, publish_date).save()

    def update_package(self, package_name, version, publish_date):
        p = self.get_package(package_name)
        p.version = version
        p.publish_date = publish_date
        p.save()
