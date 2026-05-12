#!/usr/bin/env python3
"""Check that .github/skills/ and .claude/skills/ match what sync-skills.py would produce.

Exits 0 when the on-disk host copies match the canonical source byte-for-byte (modulo
the inserted "do not edit" notice in each SKILL.md). Exits non-zero on drift, naming
every drifted file and printing the exact command to fix it.

Stdlib only.
"""

from __future__ import annotations

import argparse
import filecmp
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Import sync-skills.py as a module despite its hyphenated filename.
import importlib.util as _ilu  # noqa: E402

_spec = _ilu.spec_from_file_location("sync_skills", REPO_ROOT / "scripts" / "sync-skills.py")
sync_skills = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(sync_skills)  # type: ignore[union-attr]


def _walk_relative(root: Path) -> list[Path]:
    return sorted(p.relative_to(root) for p in root.rglob("*") if p.is_file())


def _diff_trees(expected_root: Path, actual_root: Path) -> list[str]:
    """Return a list of human-readable drift descriptions. Empty list = no drift."""
    issues: list[str] = []
    expected_files = set(_walk_relative(expected_root)) if expected_root.exists() else set()
    actual_files = set(_walk_relative(actual_root)) if actual_root.exists() else set()

    for rel in sorted(expected_files - actual_files):
        issues.append(f"missing in host copy: {actual_root / rel}")
    for rel in sorted(actual_files - expected_files):
        issues.append(f"unexpected file in host copy: {actual_root / rel}")
    for rel in sorted(expected_files & actual_files):
        if not filecmp.cmp(expected_root / rel, actual_root / rel, shallow=False):
            issues.append(f"content drift: {actual_root / rel}")
    return issues


def check() -> int:
    if not sync_skills.CANONICAL.is_dir():
        sys.stderr.write(f"error: canonical source not found: {sync_skills.CANONICAL}\n")
        return 2

    with tempfile.TemporaryDirectory(prefix="dobby-skill-check-") as tmp:
        tmp_root = Path(tmp)
        sync_skills.sync(target_root=tmp_root)

        issues: list[str] = []
        for host, actual_root in sync_skills.HOST_DIRS.items():
            expected_root = tmp_root / host
            issues.extend(_diff_trees(expected_root, actual_root))

    if issues:
        print("Skill sync check FAILED. Drift detected:")
        for line in issues:
            print(f"  - {line}")
        print()
        print("To fix, edit only files under skills/<name>/ then run:")
        print("  python scripts/sync-skills.py")
        return 1

    skill_count = sum(1 for d in sync_skills.CANONICAL.iterdir() if d.is_dir())
    print(
        f"Skill sync check OK ({skill_count} skill(s) match in .github/skills/ and .claude/skills/)."
    )
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.parse_args(argv)
    return check()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
