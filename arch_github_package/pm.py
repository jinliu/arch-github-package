from pathlib import Path
import tempfile
import tarfile
import zipfile
import shutil
import subprocess
import filetype


class Pkgbuild:
    def __init__(self, repo, project_name, project_description, version):
        self.repo = repo
        self.pkgname = project_name + '-github'
        self.pkgdesc = project_description
        self.pkgver = version
        self.build_dir = Path(tempfile.mkdtemp(prefix='pkgbuild-'+self.pkgname+"-"))
        self.maintainer = 'arch-github-package <https://github.com/jinliu/arch-github-package>'

    def get_build_dir(self):
        return self.build_dir
    
    def create_pkgbuild(self, tarball_name, sha256sum):
        pkgbuild = \
f'''# Maintainer: {self.maintainer}
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
'''

        p = Path(self.build_dir/'inspect')
        p.mkdir()
        if tarball_name.endswith('.zip'):
            zipfile.ZipFile(self.build_dir/tarball_name).extractall(p)
        else:
            tarfile.open(self.build_dir/tarball_name).extractall(p)

        # descent into single directory
        d = list(p.iterdir())
        while len(d) == 1 and d[0].is_dir():
            d = list(d[0].iterdir())

        for f in d:
            if not f.is_dir():
                mod = f.stat().st_mode
                mime = None
                t = filetype.guess(f)
                if t is not None:
                    mime = t.mime

                # executable?
                if mod & 0o111 or mime == 'application/x-executable':
                    pkgbuild += f"    install -Dm755 {f} -t \"$pkgdir/usr/bin/\"\n"
                    continue

                if f.name == 'LICENSE':
                    pkgbuild += f"    install -Dm644 {f} -t \"$pkgdir/usr/share/licenses/$pkgname\"\n"
                    continue

                if f.name.startswith('README'):
                    pkgbuild += f"    install -Dm644 {f} -t \"$pkgdir/usr/share/doc/$pkgname\"\n"
                    continue

                # manpage?
                matched = False
                for section in range(1, 10):
                    if f.name.endswith(f".{section}.gz"):
                        pkgbuild += f"    install -Dm644 {f} -t \"$pkgdir/usr/share/man/man{section}/$pkgname\"\n"
                        matched = True
                        break
                if matched:
                    continue

                print(f"Unknown file type, skipped: {f}")
        
        pkgbuild += "}\n"

        (self.build_dir/'PKGBUILD').write_text(pkgbuild)

    def get_pkgname(self):
        return self.pkgname

    def build_and_install(self):
        if subprocess.call(['makepkg', '-si'], cwd=self.build_dir, env={'PACKAGER': self.maintainer}) != 0:
            raise Exception("Failed to build package")

    def cleanup(self):
        shutil.rmtree(self.get_build_dir())


if __name__ == '__main__':
    import gh
    r = gh.Releases('zix99/rare')
    p = Pkgbuild(r.get_repo_name(), r.get_project_name(), r.get_project_description(), r.get_latest_version())
    tarball_name = r.download_tarball(p.get_build_dir())
    p.create_pkgbuild(tarball_name, 'SKIP')
    print(p.get_build_dir())
