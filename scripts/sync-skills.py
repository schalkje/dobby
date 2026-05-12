#!/usr/bin/env python3
"""Sync canonical skills/ to host-discovery copies under .github/skills/ and .claude/skills/.

Canonical source: skills/<name>/
Host copies:
  .github/skills/<name>/   (GitHub Copilot CLI discovery)
  .claude/skills/<name>/   (Claude Code discovery)

For every SKILL.md, a "do not edit — this is a copy" notice is inserted immediately
after the closing YAML frontmatter delimiter. All other files (helper scripts,
templates) are copied byte-for-byte. Skill folders present in a host directory but
absent from the canonical source are removed from the host directory.

Stdlib only — runs anywhere Python 3 is installed.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CANONICAL = REPO_ROOT / "skills"
HOST_DIRS = {
    "copilot": REPO_ROOT / ".github" / "skills",
    "claude": REPO_ROOT / ".claude" / "skills",
}

NOTICE_TEMPLATE = (
    "<!-- This file is a copy of `skills/{name}/SKILL.md` "
    "— edit the source, not this copy. Regenerate with "
    "`python scripts/sync-skills.py`. -->\n"
)


def render_skill_md(source_text: str, skill_name: str) -> str:
    """Return source_text with the 'do not edit' notice inserted after the YAML frontmatter.

    If the file has no YAML frontmatter (no leading '---' line), the notice is inserted
    at the very top. The original line endings are preserved.
    """
    notice = NOTICE_TEMPLATE.format(name=skill_name)
    # Detect line ending used by the source so the inserted notice matches.
    newline = "\r\n" if "\r\n" in source_text[:512] else "\n"
    if newline == "\r\n":
        notice = notice.replace("\n", "\r\n")

    lines = source_text.splitlines(keepends=True)
    if not lines or not lines[0].lstrip().startswith("---"):
        return notice + ("" if source_text.startswith(("\n", "\r")) else newline) + source_text

    # Find the closing frontmatter delimiter (the second '---' line).
    close_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            close_idx = i
            break
    if close_idx is None:
        # Malformed frontmatter; fall back to prepending.
        return notice + newline + source_text

    head = "".join(lines[: close_idx + 1])
    tail = "".join(lines[close_idx + 1 :])
    # Insert one blank line between the closing '---' and the notice for readability.
    return head + newline + notice + tail


def copy_skill(skill_dir: Path, dest_root: Path) -> None:
    name = skill_dir.name
    dest = dest_root / name
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)

    for src_path in sorted(skill_dir.rglob("*")):
        rel = src_path.relative_to(skill_dir)
        dst_path = dest / rel
        if src_path.is_dir():
            dst_path.mkdir(parents=True, exist_ok=True)
            continue
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        if rel.as_posix() == "SKILL.md":
            rendered = render_skill_md(src_path.read_text(encoding="utf-8"), name)
            dst_path.write_text(rendered, encoding="utf-8", newline="")
        else:
            shutil.copyfile(src_path, dst_path)


def prune_orphans(dest_root: Path, valid_names: set[str]) -> list[str]:
    removed: list[str] = []
    if not dest_root.exists():
        return removed
    for child in sorted(dest_root.iterdir()):
        if child.is_dir() and child.name not in valid_names:
            shutil.rmtree(child)
            removed.append(child.name)
    return removed


def sync(target_root: Path | None = None) -> dict:
    """Sync canonical to host dirs.

    If target_root is None, syncs the real host directories. Otherwise syncs into
    target_root/<host>/skills/ — used by check-skill-sync.py to generate into a temp dir.
    """
    if not CANONICAL.is_dir():
        sys.stderr.write(f"error: canonical source not found: {CANONICAL}\n")
        sys.exit(2)

    skill_dirs = sorted(d for d in CANONICAL.iterdir() if d.is_dir())
    skill_names = {d.name for d in skill_dirs}

    summary: dict = {"hosts": {}}
    for host, default_dest in HOST_DIRS.items():
        if target_root is not None:
            dest_root = target_root / host
        else:
            dest_root = default_dest
        dest_root.mkdir(parents=True, exist_ok=True)
        for skill_dir in skill_dirs:
            copy_skill(skill_dir, dest_root)
        removed = prune_orphans(dest_root, skill_names)
        summary["hosts"][host] = {
            "dest": str(dest_root),
            "synced": [d.name for d in skill_dirs],
            "removed": removed,
        }
    return summary


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--quiet", action="store_true", help="Suppress per-host summary output."
    )
    args = parser.parse_args(argv)

    summary = sync()
    if not args.quiet:
        for host, info in summary["hosts"].items():
            print(f"{host}: wrote {len(info['synced'])} skill(s) to {info['dest']}")
            for name in info["synced"]:
                print(f"  + {name}")
            for name in info["removed"]:
                print(f"  - {name} (removed orphan)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
