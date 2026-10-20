#!/bin/sh
# build.sh -- build package(s) from this repository with a local
# void-packages checkout. Run this on the Void host, not inside the dev
# container (xbps-src needs a chroot there).
#
#   scripts/build.sh [--install] PKG...
#
# Steps:
#   1. copy srcpkgs/PKG into $VOID_PACKAGES/srcpkgs (scripts/sync.sh)
#   2. bootstrap the masterdir on first use
#   3. run `xbps-src pkg PKG`
#   4. copy the built .xbps files into out/ (git-ignored, local to this repo)
#   5. print (or, with --install, run) the matching xbps-install command
#
# $VOID_PACKAGES defaults to ~/.local/share/void-packages.

set -eu

prog=${0##*/}
VOID_PACKAGES=${VOID_PACKAGES:-"$HOME/.local/share/void-packages"}

msg() { printf '%s\n' "$*"; }
warn() { printf '%s: warning: %s\n' "$prog" "$*" >&2; }
die() { printf '%s: error: %s\n' "$prog" "$*" >&2; exit 1; }

usage() {
	cat <<EOF
usage: $prog [--install] PKG...

Build PKG from this repository using the void-packages checkout in
\$VOID_PACKAGES (default: ~/.local/share/void-packages). The template is
copied into that checkout first (scripts/sync.sh). Freshly built .xbps
files are collected in out/ inside this repository.

  --install   install the freshly built package(s) afterwards (needs sudo)
EOF
}

install=0
pkgs=

while [ $# -gt 0 ]; do
	case $1 in
		-i | --install) install=1 ;;
		-h | --help) usage; exit 0 ;;
		--) ;;
		-*) die "unknown option: $1 (see --help)" ;;
		*) pkgs="$pkgs $1" ;;
	esac
	shift
done

if [ -z "$pkgs" ]; then
	usage >&2
	exit 2
fi
pkgs=${pkgs# }

repo_dir=$(CDPATH= cd -P "$(dirname "$0")/.." && pwd)

[ -d "$VOID_PACKAGES" ] || die "VOID_PACKAGES=$VOID_PACKAGES does not exist (run this on the Void host)"
vp=$(CDPATH= cd -P "$VOID_PACKAGES" && pwd)
[ -x "$vp/xbps-src" ] || die "$vp does not look like a void-packages checkout (no xbps-src)"

# shellcheck disable=SC2086 # package names never contain whitespace
"$repo_dir/scripts/sync.sh" $pkgs

for pkg in $pkgs; do
	[ -f "$repo_dir/srcpkgs/$pkg/template" ] ||
		die "no such template: $repo_dir/srcpkgs/$pkg/template"
	if command -v xlint >/dev/null 2>&1; then
		xlint "$repo_dir/srcpkgs/$pkg/template" ||
			warn "xlint reported problems for $pkg (continuing)"
	fi
done

cd "$vp"

if [ ! -d masterdir ]; then
	msg "Bootstrapping the masterdir (first build, this takes a while) ..."
	./xbps-src binary-bootstrap
fi

# shellcheck disable=SC2086 # package names never contain whitespace
./xbps-src pkg $pkgs

# collect the built packages in out/, local to this repository;
# the "$pkg-" prefix also picks up subpackages (e.g. foot-reload-terminfo)
outdir=$repo_dir/out
copied=0
mkdir -p "$outdir"
for pkg in $pkgs; do
	# drop stale versions of the same package, so out/ never mixes them
	rm -f "$outdir/$pkg-"*.xbps
	for f in "$vp/hostdir/binpkgs/$pkg-"*.xbps; do
		[ -f "$f" ] || continue
		cp -p "$f" "$outdir/" && copied=$((copied + 1))
	done
done
if [ "$copied" -gt 0 ]; then
	msg ""
	msg "Copied $copied package file(s) to $outdir"
else
	warn "no built packages found in $vp/hostdir/binpkgs"
fi

if [ "$install" = 1 ]; then
	if command -v xbps-rindex >/dev/null 2>&1; then
		# make out/ installable as a repository; re-adding is idempotent
		xbps-rindex -a "$outdir"/*.xbps ||
			warn "xbps-rindex failed; installing anyway"
	else
		warn "xbps-rindex not found; out/ may have no repository index"
	fi
	# shellcheck disable=SC2086
	sudo xbps-install -R "$outdir" -y $pkgs
else
	msg ""
	# shellcheck disable=SC2086
	msg "To install: xbps-rindex -a $outdir/*.xbps && sudo xbps-install -R $outdir $pkgs"
fi
