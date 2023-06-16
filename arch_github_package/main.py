import subprocess
from typing import Annotated, Optional

import github
import typer
from tabulate import tabulate

from .gh import Releases
from .pm import Pkgbuild
from .state import State

app = typer.Typer()


def install_or_upgrade(releases: Releases, pkgbuild: Pkgbuild):
    tarball_name = releases.download_tarball(pkgbuild.get_build_dir())
    pkgbuild.create_pkgbuild(tarball_name, "SKIP")
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
        try:
            pkg = state.get_package(repo)
            typer.confirm(f"Repo {repo} already installed as {pkg.package_name}, reinstall?", default=True, abort=True)
        except ValueError:
            pass

        print(f"Fetching releases from {repo}...")
        try:
            releases = Releases(repo)
        except github.UnknownObjectException:
            print(f"Repo {repo} not found.")
            raise typer.Exit(1)
        except ValueError as e:
            print(e)
            raise typer.Exit(1)

        pkgbuild = Pkgbuild(releases.get_repo_name(), releases.get_project_name(), releases.get_project_description(), releases.get_latest_version())
        print(f"Installing {repo} {releases.get_latest_version()} as {pkgbuild.get_pkgname()}\n")
        install_or_upgrade(releases, pkgbuild)

        state.new_package(pkgbuild.get_pkgname(), repo, releases.get_latest_version(), releases.get_publish_date())


@app.command()
def upgrade(package: Annotated[Optional[str], typer.Argument()] = None):
    with State() as state:
        if package is None:
            packages = [[pkg,None] for pkg in state.list_packages()]
        else:
            try:
                packages = [[state.get_package(package), None]]
            except ValueError as e:
                print(e)
                raise typer.Exit(1)

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
        
        typer.confirm(f"\nUpgrade {num_updates} packages?", default=True, abort=True)
        
        for pkg, releases in packages:
            if releases is None:
                continue
            
            print(f"Upgrading {pkg.package_name} from {pkg.version} to {releases.get_latest_version()}")
            pkgbuild = Pkgbuild(releases.get_repo_name(), releases.get_project_name(), releases.get_project_description(), releases.get_latest_version())
            install_or_upgrade(releases, pkgbuild)
            
            state.update_package(pkg.package_name, releases.get_latest_version(), releases.get_publish_date())


@app.command()
def uninstall(package: str,
              force: Annotated[bool, typer.Option(help="delete package metadata even if pacman -R fails")] = False):
    with State() as state:
        try:
            pkg = state.get_package(package)
        except ValueError as e:
            print(e)
            raise typer.Exit(1)
        
        ret = subprocess.call(["sudo", "pacman", "-R", pkg.package_name])
        if ret != 0:
            if force:
                print("pacman -R failed, but continuing anyway")
            else:
                print("Failed to uninstall package")
                raise typer.Exit(1)
        pkg.remove()


if __name__ == "__main__":
    app()
