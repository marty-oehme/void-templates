# Custom void templates

This is the space for my custom void repo.

It hosts packages that are not yet (or perhaps ever) in the normal void repos,
which I've built and maintain for myself.

Use it at your own discretion but I make no promises toward any functionality, stability or non-explody-system-ness.

Currently, files in the repository are _only_ built for x86_64.
I would like to extend it to other arches at some point but it is not a priority for me,
and I do not know enough about the xbps build system to make it easily possible.

The repository can be added to xbps by adding the following to a file called (for example) `/etc/xbps.d/20-custom-repositories.conf`:

```conf
repository=https://marty-oehme.github.io/void-templates
```

Then all packages herein can be installed.

## ROADMAP

- [x] Create new builds for all contained packages
- [x] Detect changed packages from previous builds
- [x] build only for those packages
- [x] serve from custom repository
- [x] detect upstream changes and update templates
- [ ] build for multiple (appropriate) arches

## What we currently do

- [x] use renovate to open PR whenever new version of a package is released
- [x] auto-update `template` file `pkgversion` and `checksum`
- [x] publish new package version to repo once PR has succesfully been merged

## Developing packages locally

The templates live here, but they are built by a normal [void-packages](https://github.com/void-linux/void-packages) checkout. The scripts in `scripts/` copy them into that checkout (`scripts/sync.sh`), so a build always picks up the current state of this repository.

They expect the checkout at `~/.local/share/void-packages`; set `VOID_PACKAGES` if yours lives elsewhere:

```sh
export VOID_PACKAGES=$HOME/projects/void-packages
```

All of this has to run on the Void machine itself (xbps-src builds inside a chroot), not inside a container.

### Syncing templates

`scripts/sync.sh [--dry-run] [--force] PKG...` copies `srcpkgs/PKG` to `$VOID_PACKAGES/srcpkgs/PKG`. Without arguments every package is synced. Re-run it after editing a template (or just use `scripts/build.sh`, which does it for you).

- `--dry-run` only prints what would happen.
- `--remove` deletes the copies again (with arguments only for those packages, without arguments all of them).
- `--force` also replaces directories that were not copied by this script.
- Everything synced is recorded in `$VOID_PACKAGES/hostdir/.void-templates-synced`. The directory is not in that manifest is not touched at all: the package already exists upstream, and xbps-src would use that.

Why copying instead of symlinking? xbps-src reads a symlink in `srcpkgs/` as a subpackage reference (like `srcpkgs/foot-reload-terminfo -> foot-reload` in this repository), and the build chroot can only see files below the checkout.

### Checking templates and checksums

`scripts/check.py [--offline] [PKG...]` is a quick pre-flight check, not a replacement for `xlint`. It runs `sh -n`, reads the variables out of the template, checks that the required ones are present and plausible (revision, maintainer format, distfile/checksum counts, …), and then downloads the distfiles (cached in `~/.cache/void-templates/distfiles`) to verify the checksums. `--offline` skips the download. Only problems are printed.

`scripts/checksum.sh [PKG...]` downloads the distfiles and rewrites `checksum=` accordingly, the local equivalent of `xgensum -i`. A deliberate `checksum=skip` is left alone.

### Building and installing

`scripts/build.sh [--install] PKG...` syncs the template(s), runs `xlint` if it happens to be installed, bootstraps the masterdir on first use, and runs `xbps-src pkg`. The package ends up in `$VOID_PACKAGES/hostdir/binpkgs` and is copied to `out/` inside this repository (git-ignored), which is also what gets installed: with `--install` the script indexes `out/` and runs `xbps-install` against it, otherwise it prints that command.

A full cycle for a new package looks like this:

```sh
mkdir srcpkgs/newpkg
$EDITOR srcpkgs/newpkg/template
scripts/checksum.sh newpkg
scripts/build.sh --install newpkg
```

When adding additional packages, remember to add the package to the list below, and add a renovate annotation (`# renovate: datasource=... depName=...` on the line above `version=`) if the upstream releases can be tracked automatically.

## Packages

- [x] bemoji
- [x] dotter
- [x] filtile (window compositor for riverwm)
- [x] foot-reload (custom foot fork which reloads config on theme change)
- [x] git-bug
- [x] localsend-cli (localsend-go)
- [x] netbird (bin build only. After install, enable service, then run 'netbird up')
- [x] pass-coffin (plugin for pass to hide metadata, _caution_: untested and barely used)
- [x] piavpn-bin (Private Internet Access VPN client + daemon, repacked from the official installer. Service is installed as `piavpn` but not enabled: `sv up piavpn`. See INSTALL.msg on upgrade notes)
- [x] ripgrep-all
- [x] tgpt
- [x] tinty
- [x] topen
- [x] vimiv-qt

## (Potential) future packages

- [ ] ~~impala~~ (integrated upstream)
- [ ] bugwarrior - only in pypi for now
- [ ] viddy / hwatch
- [ ] protonvpn / piactl (open-source client; the official client is now packaged as `piavpn-bin`)
  - <https://github.com/pia-foss/desktop/issues/59>
- [ ] dstask
- [ ] tasklite
- [ ] tu

Note: If you find a program here that belongs to you and you'd rather not have it hosted in the repo,
please let me know and I will of course take it down.
