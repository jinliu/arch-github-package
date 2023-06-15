from .gh import Releases
from .pm import Pkgbuild
from .state import State, Package

from typing import Optional, Annotated
import typer
from tabulate import tabulate
import subprocess


app = typer.Typer()


def install_or_upgrade(releases: Releases, pkgbuild: Pkgbuild):
    print('Downloading tarball...')
    tarball_name = releases.download_tarball(pkgbuild.get_build_dir())

    print('Installing...')
    pkgbuild.create_pkgbuild(tarball_name, 'SKIP')
    pkgbuild.build_and_install()
    pkgbuild.cleanup()


@app.command()
def list():
    with State() as state:
        packages = state.list_packages()
        table = [[pkg.package_name, pkg.repo, pkg.version, pkg.publish_date] for pkg in packages]
        print(tabulate(table, headers=["Package","Repo", "Version", "Date"]))


@app.command()
def install(repo: str):
    with State() as state:
        releases = Releases(repo)
        pkgbuild = Pkgbuild(releases.get_repo_name(), releases.get_project_name(), releases.get_project_description(), releases.get_latest_version())

        print(f'Installing {repo} {releases.get_latest_version()} as {pkgbuild.get_pkgname()}')
        install_or_upgrade(releases, pkgbuild)

        state.new_package(pkgbuild.get_pkgname(), repo, releases.get_latest_version(), releases.get_publish_date())


@app.command()
def upgrade(package: Annotated[Optional[str], typer.Argument()] = None):
    with State() as state:
        if package is None:
            packages = [[pkg,None] for pkg in state.list_packages()]
        else:
            packages = [[state.get_package(package), None]]

        print("Checking for updates...\n")
        
        num_updates = 0
        releases = {}
        for i in packages:
            pkg = i[0]
            releases = Releases(pkg.repo)
            if releases.get_latest_version() == pkg.version:
                continue
            
            i[1] = releases
            num_updates += 1

        print(tabulate([[pkg.package_name, pkg.repo, pkg.version, pkg.publish_date,
                         releases and releases.get_latest_version(), releases and releases.get_publish_date()] for pkg, releases in packages],
                       headers=["Package", "Repo", "Old Version", "Date", "New Version", "Date"]))
        
        if num_updates == 0:
            print("\nNo updates available")
            return
        
        if not typer.confirm(f"\nUpgrade {num_updates} packages?", default=True):
            return

        for pkg, releases in packages:
            if releases is None:
                continue
            
            print(f'Upgrading {pkg.package_name} from {pkg.version} to {releases.get_latest_version()}')
            pkgbuild = Pkgbuild(releases.get_repo_name(), releases.get_project_name(), releases.get_project_description(), releases.get_latest_version())
            install_or_upgrade(releases, pkgbuild)
            state.update_package(pkg.package_name, releases.get_latest_version(), releases.get_publish_date())


@app.command()
def uninstall(package: str):
    with State() as state:
        p = state.get_package(package)
        ret = subprocess.call(['sudo', 'pacman', '-R', package])
        if ret != 0:
            raise Exception("Failed to uninstall package")
        state.remove_package(package)


if __name__ == "__main__":
    app()
