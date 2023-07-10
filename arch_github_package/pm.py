import gzip
import re
import shutil
import subprocess
import tarfile
import tempfile
import zipfile
from pathlib import Path

import typer


class Pkgbuild:
    def __init__(self, repo, project_name, project_description, version):
        self.repo = repo
        self.pkgname = project_name + "-github"
        self.pkgdesc = project_description.replace("'", "\\'")
        self.pkgver = version
        self.build_dir = Path(tempfile.mkdtemp(prefix="pkgbuild-"+self.pkgname+"-"))
        self.maintainer = "arch-github-package <https://github.com/jinliu/arch-github-package>"

    def get_build_dir(self):
        return self.build_dir
    
    def create_pkgbuild(self, tarball_name, sha256sum):
        pkgbuild = \
f"""# Maintainer: {self.maintainer}
pkgname={self.pkgname}
pkgver={self.pkgver}
pkgrel=1
pkgdesc='{self.pkgdesc}'
arch=('x86_64')
url="https://github.com/{self.repo}"
license=('custom')
source=({tarball_name})
sha256sums=('{sha256sum}')
package() {{
"""

        print("\nInspecting tarball...\n")
        p = Path(self.build_dir/"inspect")
        p.mkdir()
        if tarball_name.endswith(".zip"):
            zipfile.ZipFile(self.build_dir/tarball_name).extractall(p)
        else:
            try:
                tarfile.open(self.build_dir/tarball_name).extractall(p)
            except:
                if tarball_name.endswith(".gz"):
                    with gzip.open(self.build_dir/tarball_name, "rb") as f_in:
                        (p/tarball_name.removesuffix(".gz")).write_bytes(f_in.read())
                else:
                    shutil.copy(self.build_dir/tarball_name, p)

        # descent into single directory
        d = list(p.iterdir())
        while len(d) == 1 and d[0].is_dir():
            d = list(d[0].iterdir())

        for f in d:
            if not f.is_dir():
                mod = f.stat().st_mode
                mime = ""
                ret = subprocess.run(["file", "-b", "--mime-type", f], capture_output=True)
                if ret:
                    mime = ret.stdout.decode("utf-8").strip()

                # executable?
                if mod & 0o111 or "executable" in mime or "shellscript" in mime:
                    pkgbuild += f"    install -Dm755 {f} -t \"$pkgdir/usr/bin/\"\n"
                    print(f"{f.name} -> /usr/bin/{f.name}")
                    continue

                if f.name.startswith("LICENSE"):
                    pkgbuild += f"    install -Dm644 {f} -t \"$pkgdir/usr/share/licenses/$pkgname\"\n"
                    print(f"{f.name} -> /usr/share/licences/{self.pkgname}/{f.name}")
                    continue

                if f.name.endswith(".md") or f.name.startswith("README") or f.name.startswith("CHANGELOG"):
                    pkgbuild += f"    install -Dm644 {f} -t \"$pkgdir/usr/share/doc/$pkgname\"\n"
                    print(f"{f.name} -> /usr/share/doc/{self.pkgname}/{f.name}")
                    continue

                # manpage?
                matched = False
                for section in range(1, 10):
                    if f.name.endswith(f".{section}.gz"):
                        pkgbuild += f"    install -Dm644 {f} -t \"$pkgdir/usr/share/man/man{section}/$pkgname\"\n"
                        print(f"{f.name} -> /usr/share/man/man{section}/{f.name}")
                        matched = True
                        break
                if matched:
                    continue

                print(f"{f.name} -> Unknown file type {mime}, skipped.")
        
        pkgbuild += "}\n"

        typer.confirm("\nIs this OK?", default=True, abort=True)

        (self.build_dir/"PKGBUILD").write_text(pkgbuild)

    def get_pkgname(self):
        return self.pkgname

    def build_and_install(self):
        if subprocess.call(["makepkg", "-si"], cwd=self.build_dir, env={"PACKAGER": self.maintainer}) != 0:
            raise Exception("Failed to build package")

    def cleanup(self):
        shutil.rmtree(self.get_build_dir())
