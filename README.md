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
- [ ] detect upstream changes and update templates
- [ ] build for multiple (appropriate) arches

## Package wishlist

- [x] bemoji
- [x] ripgrep-all
- [x] filtile (/src instead of bin)
- [x] dotter (/src instead of bin)
- [x] git-bug (/src)
- [ ] bugwarrior - only in pypi for now
- [ ] viddy / hwatch
- [ ] netbird / protonvpn / piactl
  - <https://github.com/pia-foss/desktop/issues/59>
- [ ] taskopen
- [ ] dstask
- [ ] tasklite
- [ ] tu
- [ ] <https://github.com/nushell/nufmt>
- [x] tgpt

- [ ] impala (iwd TUI)
- [ ] localsend:

  - [ ] localsend
  - [x] localsend-cli (localsend-go)

- gitleaks?
- syncall - in pypi for now

## Auto updating

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
