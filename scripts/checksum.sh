#!/bin/sh
# checksum.sh -- local stand-in for `xgensum -i`.
#
#   scripts/checksum.sh [PKG...]
#
# Downloads the distfiles of the given templates (default: all of them) and
# rewrites their checksum= lines. Handles the common single/multi-distfile
# case; should you ever hit something exotic (git sources, renamed distfiles
# with special handling, etc.), fall back to `xgensum -i` inside a
# void-packages checkout.

set -eu

repo_dir=$(CDPATH= cd -P "$(dirname "$0")/.." && pwd)

exec python3 "$repo_dir/scripts/check.py" --write-checksums "$@"
