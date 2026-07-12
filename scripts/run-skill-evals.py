#!/usr/bin/env python3
"""Validate and drive dobby's skill evals.

Skill evals live next to each skill source as `evals/evals.json`
(e.g. skills/github/dobby-create-pbi/evals/evals.json) and are bundled into
generated output by build-skills.py. Two eval kinds:

  behavior  Run the scenario in a fresh agent session with the skill installed
            and grade the transcript against `expected` / `forbidden`.
  pressure  A behavior eval whose scenario actively tempts the agent to break
            a discipline rule (never auto-retry creation, never `gh issue
            close`, ...). The rule must hold under pressure.

`description_tuning` holds should-trigger / should-not-trigger prompts for
measuring whether the skill's description fires at the right moments.

Modes:
  --validate      Schema-check every evals.json (used by CI). Exit non-zero on
                  any violation.
  --list          Print a summary table of all evals.
  --run-sheet F   Emit a markdown run sheet to F: one section per eval with
                  the scenario prompt to paste into a fresh session and the
                  grading checklist. Running the sessions and grading is
                  model-in-the-loop and deliberately not automated here — use
                  the skill-creator plugin's eval harness for automated
                  grading, or grade the run sheet by hand.

Python standard library only.
"""

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILLS = REPO / "skills"

REQUIRED_EVAL_KEYS = {"id", "kind", "scenario", "setup", "expected", "forbidden"}
KINDS = {"behavior", "pressure"}


def find_eval_files():
    return sorted(SKILLS.glob("*/*/evals/evals.json"))


def validate_file(path):
    problems = []
    rel = path.relative_to(REPO).as_posix()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [f"{rel}: invalid JSON — {e}"]

    skill_dir = path.parent.parent.name
    if data.get("skill") != skill_dir:
        problems.append(f"{rel}: 'skill' is {data.get('skill')!r}, expected the skill dir name {skill_dir!r}")

    tuning = data.get("description_tuning", {})
    for key in ("should_trigger", "should_not_trigger"):
        prompts = tuning.get(key, [])
        if not isinstance(prompts, list) or len(prompts) < 2:
            problems.append(f"{rel}: description_tuning.{key} needs a list of >= 2 prompts")

    evals = data.get("evals", [])
    if len(evals) < 3:
        problems.append(f"{rel}: needs >= 3 evals (has {len(evals)})")
    if not any(e.get("kind") == "pressure" for e in evals):
        problems.append(f"{rel}: needs at least one 'pressure' eval for its discipline rules")

    seen = set()
    for e in evals:
        eid = e.get("id", "<missing id>")
        missing = REQUIRED_EVAL_KEYS - set(e)
        if missing:
            problems.append(f"{rel}: eval '{eid}' missing keys: {', '.join(sorted(missing))}")
        if e.get("kind") not in KINDS:
            problems.append(f"{rel}: eval '{eid}' kind must be one of {sorted(KINDS)}")
        for lk in ("expected", "forbidden"):
            if lk in e and (not isinstance(e[lk], list) or not all(isinstance(x, str) for x in e[lk])):
                problems.append(f"{rel}: eval '{eid}'.{lk} must be a list of strings")
        if not e.get("expected"):
            problems.append(f"{rel}: eval '{eid}' has no expected behaviors")
        if eid in seen:
            problems.append(f"{rel}: duplicate eval id '{eid}'")
        seen.add(eid)
    return problems


def cmd_validate(files):
    problems = []
    for f in files:
        problems += validate_file(f)
    if problems:
        print("[FAIL] skill eval validation:", file=sys.stderr)
        for p in problems:
            print(f"  {p}", file=sys.stderr)
        return 1
    print(f"[ok] {len(files)} eval file(s) valid")
    return 0


def cmd_list(files):
    for f in files:
        data = json.loads(f.read_text(encoding="utf-8"))
        tier = f.relative_to(SKILLS).parts[0]
        print(f"{data['skill']}  ({tier})")
        for e in data.get("evals", []):
            print(f"  [{e['kind']:8}] {e['id']}")
        t = data.get("description_tuning", {})
        print(f"  [trigger ] {len(t.get('should_trigger', []))} should / {len(t.get('should_not_trigger', []))} should-not prompts")
    return 0


def cmd_run_sheet(files, out):
    lines = ["# Skill eval run sheet", "",
             "For each eval: start a **fresh** agent session in a sandbox project with the",
             "generated scenario skills installed, arrange the `setup`, paste the `scenario`",
             "as the user prompt, then grade the transcript against the checklists.",
             "Grade description tuning by pasting each trigger prompt into a fresh session",
             "and recording whether the skill fired.", ""]
    for f in files:
        data = json.loads(f.read_text(encoding="utf-8"))
        lines += [f"## {data['skill']}", ""]
        for e in data.get("evals", []):
            lines += [f"### {e['id']}  `{e['kind']}`", "",
                      f"**Setup**: {e['setup']}", "",
                      "**Prompt to paste**:", "", "```", e["scenario"], "```", "",
                      "**Must observe**:"]
            lines += [f"- [ ] {x}" for x in e["expected"]]
            lines += ["", "**Must NOT observe**:"]
            lines += [f"- [ ] (absent) {x}" for x in e["forbidden"]]
            lines.append("")
        t = data.get("description_tuning", {})
        lines += ["### description tuning", "", "**Should trigger the skill**:"]
        lines += [f"- [ ] {p}" for p in t.get("should_trigger", [])]
        lines += ["", "**Should NOT trigger the skill**:"]
        lines += [f"- [ ] {p}" for p in t.get("should_not_trigger", [])]
        lines.append("")
    Path(out).write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"[ok] run sheet written to {out}")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="run-skill-evals.py", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--validate", action="store_true", help="schema-check every evals.json (CI)")
    g.add_argument("--list", action="store_true", help="summarize all evals")
    g.add_argument("--run-sheet", metavar="FILE", help="emit a markdown run sheet")
    args = p.parse_args(argv)

    files = find_eval_files()
    if not files:
        print("[FAIL] no evals.json files found under skills/*/*/evals/", file=sys.stderr)
        return 1
    if args.validate:
        return cmd_validate(files)
    if args.list:
        return cmd_list(files)
    return cmd_run_sheet(files, args.run_sheet)


if __name__ == "__main__":
    sys.exit(main())
