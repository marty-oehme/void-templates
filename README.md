# Custom void templates

This is the space for my custom void repo.

It hosts packages that are not yet (or perhaps ever) in the normal void repos,
which I've built and maintain for myself.

Use it at your own discretion but I make no promises toward any functionality, stability or non-explody-system-ness.

## ROADMAP

### Current

- [x] Create new builds for all contained packages
- [x] Detect changed packages from previous builds
- [x] build only for those packages
- [ ] detect upstream changes and update templates
- [ ] build for multiple (appropriate) arches

### Ideas

Goal: auto-update templates on remote updates (checked e.g. every 24h)

- [ ] use renovate to auto-update `template` file pkgversion
  - <https://docs.renovatebot.com/user-stories/maintaining-aur-packages-with-renovate>
- [ ] open PR for new version
- [ ] For each PR:

  - update checksum for new version
    - [ ] grab it from correct place if it is published
    - [ ] default to recalculate checksum for new version files
    - [ ] auto-commit to PR
  - [ ] see if file structure changed?
    - Can't do this here tbh since we need to compare the output of build operation for old and new
  - [ ] if checksum OK, automatically commit to `main` branch

- [ ] on new `main` addition
- [ ] complete builds

  - only build for new packages?

- [ ] publish new repo version:
  - [ ] pull all existing packages in repo into dir
  - [ ] put new version of the package into repo
  - [ ] repush repo to page with new file

## Package wishlist

Packages I didn't find in repos:

- [ ] bemoji
- [ ] bugwarrior
- [ ] viddy
- [ ] netbird / protonvpn / piactl
- [ ] ripgrep-all

packages built xbps-src style:

- [x] filtile (/src instead of bin)
- [x] dotter (/src instead of bin)
- [x] git-bug (/src)
- [~] git-delta
- [ ] bugwarrior
- [ ] viddy
- [ ] netbird
- [ ] piactl/daemon

  - <https://github.com/pia-foss/desktop/issues/59>

- packages to investigate:
  - [ ] impala (iwd TUI)
  - [ ] localsend
