#!/bin/sh
# sync.sh -- copy this repository's templates into a void-packages checkout.
#
#   scripts/sync.sh [--dry-run] [--force] [PKG...]
#   scripts/sync.sh --remove [PKG...]
#
# Copies srcpkgs/<pkg> into <void-packages>/srcpkgs/<pkg> so that xbps-src
# builds the templates you edit here. Symlinks do not work for this: xbps-src
# treats a symlink in srcpkgs/ as a subpackage reference, and the build chroot
# can only see files below the checkout. Re-run after every edit;
# scripts/build.sh does it automatically before building.
#
# Subpackage symlinks of this repository (e.g. foot-reload-terminfo ->
# foot-reload) are recreated as-is, matching the void-packages convention.
#
# The checkout is taken from $VOID_PACKAGES (default: ~/.local/share/void-packages).
# Everything copied over is recorded in <void-packages>/hostdir/.void-templates-synced,
# which is what keeps this script from ever overwriting an upstream package
# that happens to have the same name.

set -eu

prog=${0##*/}
VOID_PACKAGES=${VOID_PACKAGES:-"$HOME/.local/share/void-packages"}

msg() { printf '%s\n' "$*"; }
warn() { printf '%s: warning: %s\n' "$prog" "$*" >&2; }
die() { printf '%s: error: %s\n' "$prog" "$*" >&2; exit 1; }

usage() {
	cat <<EOF
usage: $prog [--dry-run] [--force] [PKG...]
       $prog --remove [PKG...]
Copy this repository's srcpkgs/* into a void-packages checkout
(\$VOID_PACKAGES, default: ~/.local/share/void-packages), so that xbps-src
builds the templates you edit here. Re-run after editing a template.

  PKG...      only act on these packages (default: everything in srcpkgs/)
  --remove    remove the copies again (e.g. before sending a template upstream)
  --dry-run   show what would happen and change nothing
  --force     also replace directories that were not copied by this script
              (by default only packages recorded in the sync manifest, or
              leftovers of scripts/link.sh, are replaced)
EOF
}

# absolute target of a symlink, also when the target is dangling (best effort)
link_target() {
	# GNU realpath needs -m to resolve dangling links, busybox (no -m) does it
	# anyway, so try both before falling back to a physical cd.
	if command -v realpath >/dev/null 2>&1; then
		realpath -m "$1" 2>/dev/null && return 0
		realpath "$1" 2>/dev/null && return 0
	fi
	( CDPATH= cd -P "$(dirname "$1")" && CDPATH= cd -P "$(readlink "$1")" && pwd ) 2>/dev/null
}

mode=sync
dry_run=0
force=0
pkgs=

while [ $# -gt 0 ]; do
	case $1 in
		-r | --remove) mode=remove ;;
		-n | --dry-run) dry_run=1 ;;
		-f | --force) force=1 ;;
		-h | --help) usage; exit 0 ;;
		--) ;;
		-*) die "unknown option: $1 (see --help)" ;;
		*) pkgs="$pkgs $1" ;;
	esac
	shift
done

repo_dir=$(CDPATH= cd -P "$(dirname "$0")/.." && pwd)
srcpkgs_dir=$repo_dir/srcpkgs

[ -d "$srcpkgs_dir" ] || die "no srcpkgs/ directory in $repo_dir"
[ -d "$VOID_PACKAGES" ] || die "VOID_PACKAGES=$VOID_PACKAGES does not exist"
vp=$(CDPATH= cd -P "$VOID_PACKAGES" && pwd)
[ -x "$vp/xbps-src" ] || die "$vp does not look like a void-packages checkout (no xbps-src)"
[ -d "$vp/srcpkgs" ] || die "$vp has no srcpkgs/ directory"

manifest=$vp/hostdir/.void-templates-synced

in_manifest() {
	[ -f "$manifest" ] && grep -qxF "$1" "$manifest" 2>/dev/null
}

manifest_add() {
	[ "$dry_run" = 1 ] && return 0
	mkdir -p "${manifest%/*}"
	touch "$manifest"
	grep -qxF "$1" "$manifest" 2>/dev/null || printf '%s\n' "$1" >>"$manifest"
}

manifest_del() {
	[ "$dry_run" = 1 ] && return 0
	[ -f "$manifest" ] || return 0
	grep -vxF "$1" "$manifest" >"$manifest.tmp" 2>/dev/null || true
	mv "$manifest.tmp" "$manifest"
}

synced=0
kept=0
skipped=0
removed=0

sync_one() {
	_name=$1
	_src=$srcpkgs_dir/$_name
	_dst=$vp/srcpkgs/$_name

	if [ -L "$_src" ]; then
		# subpackage symlink of this repository: recreate it verbatim
		_link=$(readlink "$_src")
		if [ -L "$_dst" ] && [ "$(readlink "$_dst")" = "$_link" ]; then
			kept=$((kept + 1))
			return 0
		fi
		_ours=0
		if in_manifest "$_name"; then _ours=1; fi
		if [ "$_ours" = 0 ] && [ -L "$_dst" ]; then
			_target=$(link_target "$_dst") || _target=
			case ${_target:-} in
				"$srcpkgs_dir"/*) _ours=1 ;; # leftover of scripts/link.sh
			esac
		fi
		if [ "$_ours" = 0 ] && [ -e "$_dst" ] && [ "$force" = 0 ]; then
			warn "$_dst already exists (that package name is taken in void-packages); not syncing $_name"
			skipped=$((skipped + 1))
			return 0
		fi
		msg "link $_dst -> $_link"
		if [ "$dry_run" = 0 ]; then
			rm -rf "$_dst"
			ln -s "$_link" "$_dst"
			manifest_add "$_name"
		fi
		synced=$((synced + 1))
		return 0
	fi

	if [ -L "$_dst" ]; then
		_target=$(link_target "$_dst") || _target=
		case ${_target:-} in
			"$srcpkgs_dir"/*) ;; # leftover of scripts/link.sh: replace it
			*)
				if [ "$force" = 1 ]; then
					msg "replace $_dst (was a symlink to '$(readlink "$_dst")')"
					if [ "$dry_run" = 0 ]; then rm -rf "$_dst"; fi
				else
					warn "$_dst is a symlink to '$(readlink "$_dst")'; use --force to replace it"
					skipped=$((skipped + 1))
					return 0
				fi
				;;
		esac
	elif [ -e "$_dst" ]; then
		if in_manifest "$_name"; then
			:
		elif [ "$force" = 1 ]; then
			msg "replace $_dst (not created by $prog)"
		else
			warn "$_dst already exists (that package name is taken in void-packages); not syncing $_name"
			skipped=$((skipped + 1))
			return 0
		fi
	fi

	if [ -e "$_dst" ] && [ ! -L "$_dst" ] && [ "$dry_run" = 0 ] &&
		command -v diff >/dev/null 2>&1 &&
		diff -r -q "$_src" "$_dst" >/dev/null 2>&1; then
		kept=$((kept + 1))
		return 0
	fi

	msg "sync $_dst"
	if [ "$dry_run" = 0 ]; then
		rm -rf "$_dst"
		cp -a "$_src" "$_dst"
		manifest_add "$_name"
	fi
	synced=$((synced + 1))
}

remove_one() {
	_name=$1
	_dst=$vp/srcpkgs/$_name

	if [ -L "$_dst" ]; then
		_target=$(link_target "$_dst") || _target=
		case ${_target:-} in
			"$srcpkgs_dir"/*) ;; # leftover of scripts/link.sh
			*)
				# a real subpackage symlink we created (e.g. foot-reload-terminfo)
				in_manifest "$_name" || return 0 ;;
		esac
	elif ! in_manifest "$_name"; then
		return 0
	fi

	msg "remove $_dst"
	if [ "$dry_run" = 0 ]; then
		rm -rf "$_dst"
		manifest_del "$_name"
	fi
	removed=$((removed + 1))
}

if [ -n "$pkgs" ]; then
	for pkg in $pkgs; do
		if [ "$mode" = sync ] && [ ! -e "$srcpkgs_dir/$pkg" ]; then
			die "no such package in $srcpkgs_dir: $pkg"
		fi
		if [ "$mode" = sync ]; then
			sync_one "$pkg"
		else
			remove_one "$pkg"
		fi
	done
elif [ "$mode" = sync ]; then
	for _src in "$srcpkgs_dir"/*; do
		[ -e "$_src" ] || continue
		sync_one "${_src##*/}"
	done
else
	# remove everything this script ever copied, plus any leftover of link.sh
	for _dst in "$vp"/srcpkgs/*; do
		[ -e "$_dst" ] || [ -L "$_dst" ] || continue
		remove_one "${_dst##*/}"
	done
fi

if [ "$mode" = sync ]; then
	msg ""
	msg "synced: $synced, already up to date: $kept, skipped: $skipped"
else
	msg ""
	msg "removed: $removed"
fi
if [ "$dry_run" = 1 ]; then
	msg "(dry run: nothing was changed)"
fi
