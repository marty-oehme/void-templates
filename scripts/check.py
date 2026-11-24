#!/usr/bin/env python3
"""Pre-flight checks for the xbps templates in this repository.

This is deliberately *not* xlint: xlint needs a full void-packages checkout
and knows more about packaging policy. These checks catch the mistakes that
are cheap to catch while a template is being written:

    * POSIX sh syntax of the template
    * presence and shape of the required variables
    * distfile URLs that can be fetched, and checksums that match them
    * optionally rewriting checksum= from the current distfiles
      (--write-checksums, the local equivalent of `xgensum -i`)
    * the version/revision policy against a base revision (--base REF), so
      that clients actually see the rebuilt package

Usage:
    scripts/check.py [--offline] [--write-checksums] [--base REF] [PKG...]

Exit status is 0 when no errors were found; warnings do not fail the run.
"""

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
SRCPKGS_DIR = REPO_DIR / "srcpkgs"

# Variables the template is expected to set; we read them by sourcing the
# template in a POSIX shell, exactly like xbps-src does.
WANTED_VARS = (
    "pkgname",
    "version",
    "revision",
    "short_desc",
    "maintainer",
    "license",
    "homepage",
    "distfiles",
    "checksum",
    "build_style",
)

# Variables xbps-src provides to templates but which do not live in them.
# Needed to expand ${PYPI_SITE} & friends when checking distfile URLs.
SITE_VARS = {
    "PYPI_SITE": "https://files.pythonhosted.org/packages/source",
    "GNU_SITE": "https://ftp.gnu.org/gnu",
    "SOURCEFORGE_SITE": "https://downloads.sourceforge.net/sourceforge",
    "KDE_SITE": "https://download.kde.org/stable",
    "GNOME_SITE": "https://download.gnome.org/sources",
    "X11_SITE": "https://www.x.org/releases/individual",
    "MOZILLA_SITE": "https://ftp.mozilla.org/pub",
}

USER_AGENT = "void-templates-check/1.0 (+https://github.com/marty-oehme/void-templates)"
CHECKSUM_RE = re.compile(r"^[0-9a-f]{64}$")
VAR_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}|\$([A-Za-z_][A-Za-z0-9_]*)")
# Strict single-line patterns for the base template: it is untrusted, so it is
# never sourced, only these values are read out of it.
BASE_VERSION_RE = re.compile(r"^version=(.*)$", re.MULTILINE)
BASE_REVISION_RE = re.compile(r"^revision=(.*)$", re.MULTILINE)


class PackageResult:
    def __init__(self, name):
        self.name = name
        self.errors = []
        self.warnings = []
        self.updated = False

    def error(self, message):
        self.errors.append(message)

    def warn(self, message):
        self.warnings.append(message)

    @property
    def ok(self):
        return not self.errors


def load_template(path):
    """Return (variables, error). Sourcing is safe: templates only define
    variables and functions, nothing runs at top level."""
    syntax = subprocess.run(["sh", "-n", str(path)], capture_output=True, text=True)
    if syntax.returncode != 0:
        return None, syntax.stderr.strip() or "shell syntax error"

    # xbps-src defines the *_SITE variables before sourcing a template, so the
    # template's distfiles=... is expanded at assignment time. Do the same,
    # otherwise ${PYPI_SITE} would expand to nothing here.
    prelude = "".join("%s='%s'\n" % (name, value) for name, value in SITE_VARS.items())
    dumper = (
        prelude
        + '. "$1" >/dev/null 2>&1\n'
        + "".join("printf '%%s\\0' \"${%s-}\"\n" % name for name in WANTED_VARS)
    )
    proc = subprocess.run(
        ["sh", "-c", dumper, "sh", str(path)], capture_output=True
    )
    if proc.returncode != 0:
        return None, proc.stderr.decode(errors="replace").strip() or "could not read template"

    chunks = proc.stdout.split(b"\0")
    values = {}
    for index, name in enumerate(WANTED_VARS):
        raw = chunks[index] if index < len(chunks) else b""
        values[name] = raw.decode(errors="replace")
    return values, None


def expand(value, values):
    """Expand $VAR / ${VAR} using template values and known xbps-src sites.
    Returns (expanded, unresolved_names)."""
    unresolved = set()

    def replace(match):
        name = match.group(1) or match.group(2)
        if values.get(name):
            return values[name]
        if name in SITE_VARS:
            return SITE_VARS[name]
        unresolved.add(name)
        return match.group(0)

    return VAR_RE.sub(replace, value), unresolved


def distfile_list(values):
    """Split distfiles into [(url, rename)], honouring the '>name' syntax."""
    entries = []
    for token in values.get("distfiles", "").split():
        url, sep, rename = token.partition(">")
        entries.append((url, rename if sep else None))
    return entries


def cache_dir():
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    path = Path(base) / "void-templates" / "distfiles"
    path.mkdir(parents=True, exist_ok=True)
    return path


def fetch(url):
    parsed = urllib.parse.urlparse(url)
    basename = os.path.basename(parsed.path) or "distfile"
    prefix = hashlib.sha256(url.encode()).hexdigest()[:16]
    destination = cache_dir() / f"{prefix}-{basename}"
    if destination.is_file() and destination.stat().st_size > 0:
        return destination

    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    partial = destination.with_name(destination.name + ".part")
    try:
        with urllib.request.urlopen(request, timeout=120) as response, open(partial, "wb") as handle:
            shutil.copyfileobj(response, handle, 256 * 1024)
    except BaseException:
        partial.unlink(missing_ok=True)
        raise
    partial.replace(destination)
    return destination


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def rewrite_checksum(path, hashes):
    """Replace the (possibly quoted, possibly multi-line) checksum= line."""
    value = hashes[0] if len(hashes) == 1 else '"' + " ".join(hashes) + '"'
    lines = path.read_text().splitlines(keepends=True)

    start = None
    for index, line in enumerate(lines):
        if re.match(r"^checksum\s*=", line):
            start = index
            break

    if start is None:
        # no checksum line yet: put it right after the last distfiles line
        insert_at = len(lines)
        for index, line in enumerate(lines):
            if re.match(r"^distfiles\s*=", line):
                insert_at = index + 1
                while insert_at < len(lines) and not re.match(
                    r"^[A-Za-z_][A-Za-z0-9_]*=", lines[insert_at]
                ):
                    insert_at += 1
        lines.insert(insert_at, f"checksum={value}\n")
    else:
        end = start
        current = lines[start].split("=", 1)[1].strip()
        while current.startswith('"') and current.count('"') % 2 == 1 and end + 1 < len(lines):
            end += 1
            current += lines[end]
        lines[start : end + 1] = [f"checksum={value}\n"]

    path.write_text("".join(lines))


def git(*args):
    return subprocess.run(
        ["git", "-C", str(REPO_DIR), *args], capture_output=True, text=True
    )


def package_paths(name):
    """Return the srcpkgs paths that make up a package, following symlinks.

    git does not resolve symlinks in tree paths, so `srcpkgs/X/template` fails
    when X links to another package. Both the entry and its target are returned.
    """
    paths = [f"srcpkgs/{name}"]
    resolved = (SRCPKGS_DIR / name).resolve()
    try:
        relative = resolved.relative_to(SRCPKGS_DIR.resolve())
    except ValueError:
        return paths
    if len(relative.parts) == 1:
        target = f"srcpkgs/{relative.parts[0]}"
        if target not in paths:
            paths.append(target)
    return paths


def parse_base_template(text):
    """Read only version and revision from a base template.

    The base text is untrusted: it is never sourced. revision defaults to 1,
    which is what xbps-src assumes when a template does not set it.
    """
    def value(pattern, default=""):
        match = pattern.search(text)
        if not match:
            return default
        found = match.group(1).strip()
        if len(found) >= 2 and found[0] == found[-1] and found[0] in "'\"":
            found = found[1:-1].strip()
        return found

    return {
        "version": value(BASE_VERSION_RE),
        "revision": value(BASE_REVISION_RE, "1"),
    }


class BaseRevision:
    """A git commit the working tree is compared against (--base)."""

    def __init__(self, ref, commit):
        self.ref = ref
        self.commit = commit

    def template(self, name):
        """Return the base template text, or None if the package is new."""
        for path in package_paths(name):
            proc = git("show", f"{self.commit}:{path}/template")
            if proc.returncode == 0:
                return proc.stdout
        return None

    def changed(self, name):
        """Return whether the package differs from base, or None if unknown."""
        paths = package_paths(name)
        diff = git("diff", "--name-only", self.commit, "--", *paths)
        if diff.returncode != 0:
            return None
        untracked = git("ls-files", "--others", "--exclude-standard", "--", *paths)
        return bool(diff.stdout.strip() or untracked.stdout.strip())


def check_policy(result, name, version, revision, base):
    """Enforce xbps' version/revision policy against a base revision.

    A new version resets revision to 1; changing a package without a version
    bump needs a higher revision, or clients keep the binary they have.
    """
    text = base.template(name)
    if text is None:
        return

    old = parse_base_template(text)
    old_version = old["version"]
    old_revision = (
        int(old["revision"]) if re.fullmatch(r"[1-9][0-9]*", old["revision"]) else 1
    )

    if version != old_version:
        if revision != 1:
            result.error(
                f"version changed from {old_version or '<unset>'} to {version}, "
                f"so revision must be 1 (found {revision})"
            )
        return

    changed = base.changed(name)
    if changed is None:
        result.warn(
            f"could not determine files changed since {base.ref}; "
            "revision policy not checked"
        )
        return
    if not changed:
        return
    if revision < old_revision:
        result.error(f"revision went backwards from {old_revision} to {revision}")
    elif revision == old_revision:
        result.error(
            f"files changed since {base.ref} without a revision bump "
            f"(still {revision}); bump revision to {revision + 1}"
        )


def check_package(name, offline, write_checksums, base=None):
    result = PackageResult(name)
    path = SRCPKGS_DIR / name / "template"

    if not path.is_file():
        result.error(f"no template file at {path}")
        return result

    values, error = load_template(path)
    if values is None:
        result.error(error)
        return result

    raw = path.read_text()
    spaced = [
        i for i, line in enumerate(raw.splitlines(), 1) if re.match(r"^  +", line)
    ]
    if spaced:
        result.warn(
            "indentation should be tabs (void style), found spaces on line(s) "
            + ", ".join(str(i) for i in spaced[:5])
            + ("..." if len(spaced) > 5 else "")
        )
    if not raw.endswith("\n"):
        result.warn("no newline at end of file")

    pkgname = values["pkgname"].strip()
    if not pkgname:
        result.error("pkgname is not set")
    elif pkgname != name and not (SRCPKGS_DIR / name).is_symlink():
        result.error(f"pkgname={pkgname!r} does not match directory name {name!r}")
    elif not re.fullmatch(r"[a-z0-9][a-z0-9+._-]*", pkgname):
        result.warn(f"pkgname {pkgname!r} contains unusual characters")

    version = values["version"].strip()
    if not version:
        result.error("version is not set")
    elif re.search(r"\s", version):
        result.error("version contains whitespace")

    revision = values["revision"].strip()
    if not revision:
        result.error("revision is not set")
    elif not re.fullmatch(r"[1-9][0-9]*", revision):
        result.error(f"revision={revision!r} is not a positive integer")
    elif base is not None and version:
        check_policy(result, name, version, int(revision), base)

    short_desc = values["short_desc"].strip()
    if not short_desc:
        result.error("short_desc is not set")
    elif len(short_desc) > 80:
        result.warn(f"short_desc is {len(short_desc)} characters long (80 is usual)")

    maintainer = values["maintainer"].strip()
    if not maintainer:
        result.error("maintainer is not set")
    elif not re.fullmatch(r".+ <[^<>@\s]+@[^<>\s]+>", maintainer):
        result.warn("maintainer should look like 'Name <mail@example.org>'")

    if not values["license"].strip():
        result.error("license is not set")

    homepage = values["homepage"].strip()
    if not homepage:
        result.warn("homepage is not set")
    elif not re.match(r"https?://", homepage):
        result.warn(f"homepage {homepage!r} is not an http(s) URL")

    files = distfile_list(values)
    checksums = values["checksum"].split()
    skip_rewrite = False

    if not files:
        if checksums:
            result.warn("checksum is set but there are no distfiles")
        else:
            result.warn("no distfiles and no checksum (meta package?)")
    elif not checksums:
        if write_checksums:
            result.warn("checksum is not set (will be written)")
        else:
            result.error("checksum is not set")
    elif len(checksums) == 1 and checksums[0].lower() == "skip":
        # an explicit skip is intentional; never overwrite it
        result.warn("checksum=skip disables checksum verification")
        checksums = []
        skip_rewrite = True
    else:
        if len(checksums) != len(files):
            message = f"{len(files)} distfile(s) but {len(checksums)} checksum(s)"
            if write_checksums:
                result.warn(message + " (will be rewritten)")
            else:
                result.error(message)
        for index, checksum in enumerate(checksums):
            if not CHECKSUM_RE.match(checksum):
                message = (
                    f"checksum #{index + 1} is not a 64-character lowercase "
                    f"sha256: {checksum!r}"
                )
                if write_checksums:
                    result.warn(message + " (will be rewritten)")
                else:
                    result.error(message)

    if offline or not files:
        return result

    computed = []
    for index, (url, _rename) in enumerate(files):
        expanded, unresolved = expand(url, values)
        if unresolved:
            result.warn(
                "cannot expand "
                + ", ".join(sorted("${%s}" % name for name in unresolved))
                + f" in distfile {url!r}; skipping download"
            )
            computed.append(None)
            continue

        try:
            downloaded = fetch(expanded)
        except urllib.error.HTTPError as exc:
            result.error(f"fetching {expanded} failed: HTTP {exc.code} {exc.reason}")
            computed.append(None)
            continue
        except Exception as exc:  # noqa: BLE001 - network errors are not fatal per se
            result.warn(f"could not fetch {expanded} ({exc}); network check skipped")
            computed.append(None)
            continue

        actual = sha256(downloaded)
        computed.append(actual)

        expected = checksums[index] if index < len(checksums) else None
        if (
            expected
            and CHECKSUM_RE.match(expected)
            and expected != actual
            and not write_checksums
        ):
            result.error(
                f"checksum mismatch for {expanded}\n"
                f"        expected {expected}\n"
                f"        actual   {actual}"
            )

    if write_checksums and not skip_rewrite:
        if computed and all(computed):
            if computed != checksums:
                rewrite_checksum(path, computed)
                result.updated = True
        else:
            result.error("could not compute all checksums; checksum= left untouched")

    return result


def main(argv):
    parser = argparse.ArgumentParser(
        description="Check xbps templates in this repository before building them.",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="do not download distfiles (skips URL and checksum checks)",
    )
    parser.add_argument(
        "--write-checksums",
        action="store_true",
        help="rewrite checksum= from the downloaded distfiles (like `xgensum -i`)",
    )
    parser.add_argument(
        "--base",
        metavar="REF",
        default=None,
        help="git revision to compare version/revision policy against",
    )
    parser.add_argument("packages", nargs="*", metavar="PKG", help="package(s) to check")
    args = parser.parse_args(argv)

    if args.write_checksums and args.offline:
        parser.error("--write-checksums needs network access; do not combine it with --offline")

    base = None
    if args.base is not None:
        ref = args.base.strip()
        if not ref:
            print("No base revision given, skipping version/revision policy checks")
        elif re.fullmatch(r"0+", ref):
            print(f"Base revision {ref} is all zeros, skipping version/revision policy checks")
        else:
            proc = git("rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
            commit = proc.stdout.strip()
            if proc.returncode != 0 or not commit:
                parser.error(f"cannot resolve --base {ref!r} to a commit")
            base = BaseRevision(ref, commit)

    if args.packages:
        names = args.packages
        for name in names:
            if not (SRCPKGS_DIR / name).is_dir():
                parser.error(f"no such package in {SRCPKGS_DIR}: {name}")
    else:
        names = sorted(
            entry.name
            for entry in SRCPKGS_DIR.iterdir()
            if entry.is_dir() or (entry.is_symlink() and entry.exists())
        )

    results = [
        check_package(name, args.offline, args.write_checksums, base) for name in names
    ]

    failed = 0
    warned = 0
    updated = 0
    for result in results:
        if result.updated:
            updated += 1
        if result.errors:
            failed += 1
        elif result.warnings:
            warned += 1
        if not result.errors and not result.warnings and not result.updated:
            continue

        print(f"== {result.name}")
        for message in result.errors:
            print(f"   error: {message}")
        for message in result.warnings:
            print(f"   warning: {message}")
        if result.updated:
            print("   updated checksum=")

    print()
    print(
        f"{len(results)} package(s): "
        f"{len(results) - failed - warned} ok, {failed} with errors, {warned} with warnings"
        + (f", {updated} checksum(s) updated" if updated else "")
    )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
