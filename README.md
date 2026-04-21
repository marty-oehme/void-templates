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

## Packages

- [x] bemoji
- [x] dotter
- [x] filtile (window compositor for riverwm)
- [x] foot-reload (custom foot fork which reloads config on theme change)
- [x] git-bug
- [x] localsend-cli (localsend-go)
- [x] netbird (bin build only. After install, enable service, then run 'netbird up')
- [x] pass-coffin (plugin for pass to hide metadata, _caution_: untested and barely used)
- [x] ripgrep-all
- [x] tgpt
- [x] tinty
- [x] topen
- [x] vimiv-qt

## (Potential) future packages

- [ ] ~~impala~~ (integrated upstream)
- [ ] bugwarrior - only in pypi for now
- [ ] viddy / hwatch
- [ ] protonvpn / piactl
  - <https://github.com/pia-foss/desktop/issues/59>
- [ ] dstask
- [ ] tasklite
- [ ] tu

Note: If you find a program here that belongs to you and you'd rather not have it hosted in the repo,
please let me know and I will of course take it down.
