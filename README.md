# arch-github-package

Convert GitHub project releases to Archlinux package, with autoupdate.

## Why

A lot of packages in Archlinux's AUR are just a single PKGBUILD file that downloads the
latest release from GitHub, and many of them are human-maintained, which means that they
are not updated as soon as a new release is published.

This script provides an alternative. If a GitHub project has binary releases, it can
automatically download a release tarball, create a PKGBUILD file, makepkg, and install it.
It can also rebuild the package if a new release is found.

## Installation

```bash
pipx install arch-github-package
```

pipx installs the package in a virtualenv, so it doesn't pollute your system.

You can also use pip:

```bash
pip install --user --break-system-packages arch-github-package
```

(This will install the package in your user site-packages, not really breaking system packages.)

## Usage

### Install a package

```bash
agp install <github-repo>
```

Example:

```bash
agp install cortesi/devd
```

How does it work:

1. It looks for the latest release on GitHub.

1. It tries to find a pre-built package for your system, by looking
   for keywords like "linux", "x86-64", "x86_64", "amd64", "gnu" in
   the release assets.

1. It downloads the tarball, extracts it, and tries to dertermine which
   file goes where. E.g.:
   * If a file is ELF, or its x modbit is set, it goes to `/usr/bin`.
   * Files like *.1.gz go to `/usr/share/man`.
   * README.* go to `/usr/share/doc/<package-name>`.
   * LICENSE goes to `/usr/share/licenses/<package-name>`.

1. It creates a PKGBUILD file, and runs `makepkg -si` to build and install it.
   The package name is `<github-project-name>-github`. E.g., `ortesi/devd` becomes
   `devd-github`.

### List installed packages

```bash
agp list
```

### Check for upgrades

```bash
agp upgrade
```

You can also use `agp upgrade <package-name>` to upgrade a single package.

Note: if you run this command repeatively in quick succession, it will hit
GitHub's rate limit for anonymous API access.

### Uninstall a package

```bash
agp uninstall <package-name>
```

If you uninstall an -github package with `pacman`, it will still be listed by `agp list`.
So remember to use `agp uninstall` to remove it.

## Internals

### Package metadata

Metadata is stored under `~/.local/share/arch-github-package`.
