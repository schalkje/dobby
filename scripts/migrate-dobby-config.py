#!/usr/bin/env python3
"""One-time migration from `.dobby/azdo-defaults.json` to `.dobby/config.json`.

The legacy file is ADO-specific by name and schema. The new file accommodates
multiple trackers via a top-level `backend` selector and per-backend blocks:

    {
      "backend": "ado",                   // or "github" or "combined"
      "ado":    { "organization": ..., "project": ..., "team": ..., "devLinks": ... },
      "github": { "owner": ..., "repo": ..., ... },
      "worktree": { "enabled": false, "root": "..." }   // optional
    }

This script reads `.dobby/azdo-defaults.json`, wraps its contents in
`{ "backend": "ado", "ado": <legacy content> }`, writes `.dobby/config.json`,
and removes the legacy file only after the new file is written successfully.

Behaviour:
  * Idempotent — if `.dobby/config.json` already exists, the script exits 0
    after printing "already migrated" and makes no changes.
  * If neither file exists, exits 0 (fresh checkout — nothing to do).
  * `--dry-run` prints the resulting config to stdout without writing.
  * `--force` allows overwriting an existing `.dobby/config.json`.

Stdlib only — runs anywhere Python 3 is installed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DOBBY_DIR = REPO_ROOT / ".dobby"
LEGACY_NAME = "azdo-defaults.json"
NEW_NAME = "config.json"


def build_config(legacy: dict) -> dict:
    """Return the new-shape config wrapping the legacy ADO content."""
    return {"backend": "ado", "ado": legacy}


def migrate(dobby_dir: Path, *, dry_run: bool, force: bool, quiet: bool) -> int:
    """Run the migration. Returns process exit code."""
    legacy_path = dobby_dir / LEGACY_NAME
    new_path = dobby_dir / NEW_NAME

    if new_path.exists() and not force:
        if legacy_path.exists():
            _info(
                quiet,
                f"Both {new_path} and {legacy_path} exist. Refusing to "
                f"overwrite. Inspect them manually, then re-run with --force "
                f"if you want to replace {NEW_NAME}.",
            )
            return 1
        _info(quiet, f"{new_path} already exists — already migrated.")
        return 0

    if not legacy_path.exists():
        _info(quiet, f"No {LEGACY_NAME} found at {legacy_path} — nothing to migrate.")
        return 0

    try:
        legacy = json.loads(legacy_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"error: {legacy_path} is not valid JSON: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"error: cannot read {legacy_path}: {exc}", file=sys.stderr)
        return 1

    if not isinstance(legacy, dict):
        print(
            f"error: {legacy_path} must contain a JSON object at top level, "
            f"got {type(legacy).__name__}",
            file=sys.stderr,
        )
        return 1

    config = build_config(legacy)
    rendered = json.dumps(config, indent=2, ensure_ascii=False) + "\n"

    if dry_run:
        print(rendered, end="")
        _info(quiet, f"(dry-run) would write {new_path} and remove {legacy_path}")
        return 0

    dobby_dir.mkdir(parents=True, exist_ok=True)
    try:
        new_path.write_text(rendered, encoding="utf-8")
    except OSError as exc:
        print(f"error: cannot write {new_path}: {exc}", file=sys.stderr)
        return 1

    try:
        legacy_path.unlink()
    except OSError as exc:
        print(
            f"warning: wrote {new_path} but could not remove legacy "
            f"{legacy_path}: {exc}. Remove it manually to finish migration.",
            file=sys.stderr,
        )
        return 1

    _info(quiet, f"migrated {legacy_path} → {new_path}")
    return 0


def _info(quiet: bool, msg: str) -> None:
    if not quiet:
        print(msg)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Migrate .dobby/azdo-defaults.json to .dobby/config.json.",
    )
    parser.add_argument(
        "--dobby-dir",
        type=Path,
        default=DEFAULT_DOBBY_DIR,
        help=f"Path to the .dobby/ directory (default: {DEFAULT_DOBBY_DIR}).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the resulting config without writing or deleting anything.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow overwriting an existing config.json. Off by default.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress informational messages on stderr/stdout.",
    )
    args = parser.parse_args(argv)

    return migrate(
        args.dobby_dir.resolve(),
        dry_run=args.dry_run,
        force=args.force,
        quiet=args.quiet,
    )


if __name__ == "__main__":
    sys.exit(main())
