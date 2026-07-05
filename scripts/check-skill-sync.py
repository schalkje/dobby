#!/usr/bin/env python3
"""Check that the committed .claude/skills/ and .github/skills/ match what the
generator's `dev` mode (the **github** scenario) would produce.

Exits 0 when the on-disk host copies match the freshly assembled github scenario.
Exits non-zero on drift, naming every drifted file and printing the exact command
to fix it (`python scripts/build-skills.py dev`).

Stdlib only.
"""

from __future__ import annotations

import argparse
import filecmp
import importlib.util as _ilu
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HOSTS = (".claude/skills", ".github/skills")

# Import build-skills.py as a module despite its hyphenated filename.
_spec = _ilu.spec_from_file_location("build_skills", REPO_ROOT / "scripts" / "build-skills.py")
build_skills = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(build_skills)  # type: ignore[union-attr]


def _walk_relative(root: Path) -> list[Path]:
    return sorted(p.relative_to(root) for p in root.rglob("*") if p.is_file())


def _diff_trees(expected_root: Path, actual_root: Path) -> list[str]:
    issues: list[str] = []
    expected = set(_walk_relative(expected_root)) if expected_root.exists() else set()
    actual = set(_walk_relative(actual_root)) if actual_root.exists() else set()
    for rel in sorted(expected - actual):
        issues.append(f"missing in committed copy: {actual_root / rel}")
    for rel in sorted(actual - expected):
        issues.append(f"unexpected file in committed copy: {actual_root / rel}")
    for rel in sorted(expected & actual):
        if not filecmp.cmp(expected_root / rel, actual_root / rel, shallow=False):
            issues.append(f"content drift: {actual_root / rel}")
    return issues


def check() -> int:
    manifest = build_skills.load_manifest()
    with tempfile.TemporaryDirectory(prefix="dobby-skill-check-") as tmp:
        tmp_root = Path(tmp)
        issues: list[str] = []
        for host in HOSTS:
            expected_root = tmp_root / host
            problems = build_skills.assemble(manifest, "github", expected_root)
            if problems:
                print("Skill generation FAILED its own lint:", file=sys.stderr)
                print("\n".join(problems), file=sys.stderr)
                return 2
            issues.extend(_diff_trees(expected_root, REPO_ROOT / host))

    if issues:
        print("Skill sync check FAILED. Drift between committed copies and the github scenario:")
        for line in issues:
            print(f"  - {line}")
        print()
        print("To fix, edit only the sources under skills/ then regenerate:")
        print("  python scripts/build-skills.py dev")
        return 1

    n = len(manifest["common"]) + len(manifest["scenarios"]["github"])
    print(f"Skill sync check OK ({n} skill(s) match the github scenario in .claude/skills/ and .github/skills/).")
    return 0


def main(argv: list[str]) -> int:
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args(argv)
    return check()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
