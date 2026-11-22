#!/usr/bin/env python3
"""Stamp the xOpat release version into the installer metadata.

    python scripts/stamp_version.py 3.2.2 [--revision N] [--root DIR]

Rewrites, in place:
  installer_{win,linux}/config/config.xml               <Version>
  installer_{win,linux}/packages/xopat/meta/package.xml <Version>, <ReleaseDate>
  installer_win/version_info.txt                        filevers/prodvers + strings

Every substitution must hit exactly once. A pattern that stops matching is a
build error, not a silently unstamped installer: the release pipeline promises
that the installer reports the version of the xOpat release it was built from.
"""

import argparse
import datetime
import re
import sys
from pathlib import Path

SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-[0-9A-Za-z.]+)?$")


def substitute(path, replacements):
    # newline="" keeps the file's own line endings.
    with open(path, encoding="utf-8", newline="") as f:
        text = f.read()
    for pattern, replacement in replacements:
        text, count = re.subn(pattern, replacement, text)
        if count != 1:
            sys.exit(f"{path}: expected exactly one match of {pattern!r}, found {count}")
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    print(f"stamped {path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("version", help="xOpat release version, e.g. 3.2.2")
    parser.add_argument("--revision", default="", help="deploy-only rebuild number")
    parser.add_argument("--root", default=Path(__file__).resolve().parent.parent, type=Path)
    args = parser.parse_args()

    match = SEMVER.match(args.version)
    if not match:
        sys.exit(f"not a release version: {args.version!r}")
    if args.revision and not re.fullmatch(r"[1-9]\d*", args.revision):
        sys.exit(f"not a revision number: {args.revision!r}")

    major, minor, patch = match.groups()
    revision = args.revision or "0"
    core = f"{major}.{minor}.{patch}"
    # Qt IFW versions are digits separated by '.' or '-': a pre-release suffix
    # cannot be expressed, a deploy revision can.
    ifw_version = f"{core}-{args.revision}" if args.revision else core
    win_tuple = f"({major}, {minor}, {patch}, {revision})"
    win_string = f"{core}.{revision}"
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")

    version_tag = (r"<Version>[^<]*</Version>", f"<Version>{ifw_version}</Version>")
    date_tag = (r"<ReleaseDate>[^<]*</ReleaseDate>", f"<ReleaseDate>{today}</ReleaseDate>")

    for installer in ("installer_win", "installer_linux"):
        substitute(args.root / installer / "config" / "config.xml", [version_tag])
        substitute(
            args.root / installer / "packages" / "xopat" / "meta" / "package.xml",
            [version_tag, date_tag],
        )

    substitute(
        args.root / "installer_win" / "version_info.txt",
        [
            (r"filevers=\([^)]*\)", f"filevers={win_tuple}"),
            (r"prodvers=\([^)]*\)", f"prodvers={win_tuple}"),
            (r"(u'FileVersion', u')[^']*'", rf"\g<1>{win_string}'"),
            (r"(u'ProductVersion', u')[^']*'", rf"\g<1>{win_string}'"),
        ],
    )


if __name__ == "__main__":
    main()
