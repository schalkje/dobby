#!/usr/bin/env python3
"""Build-time assembler for scenario-specialized dobby skill sets.

Replaces the runtime dispatcher + backend architecture: instead of shipping
every backend and routing on `.dobby/config.json` at invocation, this tool
assembles a flat, scenario-specialized skill set per project from the source
tiers under `skills/` (`_lib`, `_common`, `ado`, `github`, `combined`) and a
single `skills/manifest.json`.

Modes:
  build [--out DIR]        Emit all three scenarios to DIR/<scenario>/ (default: build/).
  init  TARGET SCENARIO    Scaffold SCENARIO into TARGET/.claude/skills + TARGET/.github/skills.
  dev                      Assemble the `github` scenario into THIS repo's own
                           .claude/skills + .github/skills (the committed copies).

Python standard library only. No templating engine — generated SKILL.md files
read as plain prose; the only source-level construct is a `<!-- dobby:combined-seam:* -->`
anchor, which is substituted (combined) or stripped (all other scenarios) before output.
"""

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILLS = REPO / "skills"
MANIFEST = SKILLS / "manifest.json"
HOSTS = (".claude/skills", ".github/skills")
SCENARIOS = ("ado", "github", "combined")

# Stamped into every generated skill's metadata block. Bump on generator
# behavior changes. Deliberately NOT a git SHA: check-skill-sync.py
# regenerates and diffs, so the stamp must be stable across commits.
GENERATOR_VERSION = "2.0"

# Top-level frontmatter keys allowed by the Agent Skills spec
# (https://agentskills.io/specification). Host-specific extensions (Claude's
# `context`, `hooks`, `disable-model-invocation`, ...) must not ship in
# generated output: dobby targets both Claude Code and GitHub Copilot CLI,
# and only these fields are portable across spec-conforming hosts.
SPEC_FRONTMATTER_KEYS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
SPEC_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

# Patterns that must NOT appear in generated output. Each becomes a build failure.
FORBIDDEN = [
    (re.compile(r"\{\{|\}\}|\{%|%\}"), "template/macro syntax"),
    (re.compile(r"dobby:combined-seam:"), "leftover combined-seam anchor"),
    (re.compile(r"dobby-(ado|gh)-[a-z-]+"), "reference to a retired backend skill (dobby-ado-* / dobby-gh-*)"),
    (re.compile(r"after backend resolution", re.I), "dispatcher 'backend resolution' prose"),
    (re.compile(r"resolves?\s+`?backend`?\b.*\bfrom\b.*config\.json", re.I), "runtime backend routing prose"),
    (re.compile(r"\.(?:github|claude)/skills/"), "host-specific skills path (reference skills by name instead)"),
    (re.compile(r"\bskills/(?:ado|github|combined|_common|_lib)/"), "source-repo tier path (use a bundled-relative path instead)"),
    (re.compile(r"[A-Za-z]:\\|(?:templates|scripts|skills|docs|\.dobby|\.github|\.claude)\\[\w.-]"),
     "backslash path (the spec requires forward slashes, also on Windows)"),
]


def load_manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def split_frontmatter(text):
    """Return (frontmatter_str_without_fences, body) or (None, text) if no frontmatter."""
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            fm = text[3:end].strip("\n")
            body = text[end + 4:]
            return fm, body.lstrip("\n")
    return None, text


def set_name(frontmatter, name):
    """Rewrite (or insert) the top-level `name:` field in a frontmatter block."""
    if frontmatter is None:
        return f"name: {name}"
    if re.search(r"(?m)^name:\s*.*$", frontmatter):
        return re.sub(r"(?m)^name:\s*.*$", f"name: {name}", frontmatter, count=1)
    return f"name: {name}\n{frontmatter}"


METADATA_BLOCK_RE = re.compile(r"(?ms)^metadata:[ \t]*\n((?:[ \t]+\S.*\n?)*)")


def compute_compatibility(body, scripts):
    """Derive the spec `compatibility` string (environment requirements) from
    what the skill's prose actually invokes."""
    reqs = []
    if re.search(r"\baz (?:boards|repos|devops|account|extension)\b", body):
        reqs.append("Azure CLI (az) with the azure-devops extension, authenticated")
    if re.search(r"\bgh (?:auth|issue|pr|repo|api|label|search)\b", body):
        reqs.append("GitHub CLI (gh), authenticated")
    if scripts or re.search(r"(?m)^\s*python\s+\S", body):
        reqs.append("Python 3 (stdlib only)")
    if re.search(r"\bopenspec\b", body, re.I):
        reqs.append("OpenSpec CLI")
    if re.search(r"\bgit worktree\b", body):
        reqs.append("git 2.5+ (worktree support)")
    return "; ".join(reqs)


def inject_spec_fields(frontmatter, scenario, body, scripts):
    """Merge generator provenance into the source's `metadata:` block and add a
    computed `compatibility:` field. Source-authored metadata keys win."""
    meta = {}
    m = METADATA_BLOCK_RE.search(frontmatter)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, _, v = line.strip().partition(":")
                meta[k.strip()] = v.strip()
        frontmatter = METADATA_BLOCK_RE.sub("", frontmatter).rstrip("\n")
    meta.setdefault("author", "dobby")
    meta["scenario"] = scenario
    meta["generator"] = f"build-skills {GENERATOR_VERSION}"

    lines = [frontmatter.rstrip("\n")] if frontmatter.strip() else []
    compat = compute_compatibility(body, scripts)
    if compat and not re.search(r"(?m)^compatibility:", frontmatter):
        lines.append(f"compatibility: {compat}")
    lines.append("metadata:")
    for k, v in meta.items():
        lines.append(f"  {k}: {v}")
    return "\n".join(lines)


def validate_frontmatter(name, frontmatter):
    """Enforce the portable Agent Skills spec on generated frontmatter."""
    problems = []
    keys = re.findall(r"(?m)^([A-Za-z][\w-]*):", frontmatter or "")
    for key in keys:
        if key not in SPEC_FRONTMATTER_KEYS:
            problems.append(f"  {name}: non-portable frontmatter key '{key}' (spec allows: {', '.join(sorted(SPEC_FRONTMATTER_KEYS))})")
    fm_name = re.search(r"(?m)^name:\s*(.+)$", frontmatter or "")
    fm_name = fm_name.group(1).strip() if fm_name else ""
    if fm_name != name:
        problems.append(f"  {name}: frontmatter name '{fm_name}' does not match the skill directory name")
    if not SPEC_NAME_RE.match(fm_name) or len(fm_name) > 64:
        problems.append(f"  {name}: name violates the spec (lowercase/digits/hyphens, max 64 chars)")
    desc = re.search(r"(?m)^description:\s*(.+)$", frontmatter or "")
    desc = desc.group(1).strip() if desc else ""
    if not 1 <= len(desc) <= 1024:
        problems.append(f"  {name}: description missing or over 1024 chars ({len(desc)})")
    compat = re.search(r"(?m)^compatibility:\s*(.+)$", frontmatter or "")
    if compat and len(compat.group(1)) > 500:
        problems.append(f"  {name}: compatibility exceeds the spec's 500-char limit")
    return problems


def rewrite_script_paths(body, scripts, owner_of):
    """Rewrite any reference to a known _lib script (whatever its source path prefix)
    to its bundled output location: <owner-skill>/scripts/<script>. Bundled once per
    scenario under the owner; non-owner skills reference the owner's path."""
    for script in scripts:
        owner = owner_of[script]
        out_ref = f"{owner}/scripts/{script}"
        # Match skills/_lib/<script>, skills/<anything>/scripts/<script>, or .github/.claude variants.
        pat = re.compile(r"(?:\.?[\w./-]*?/)?(?:_lib|scripts)/" + re.escape(script))
        body = pat.sub(out_ref, body)
    return body


def apply_seam(body, seam, fragment_text):
    """Replace the seam anchor line with the fragment (combined) or strip it (others)."""
    anchor = re.compile(r"^[ \t]*<!--[ \t]*dobby:combined-seam:[\w-]+[ \t]*-->[ \t]*\n?", re.M)
    if seam and fragment_text is not None:
        return anchor.sub(fragment_text.rstrip("\n") + "\n", body)
    return anchor.sub("", body)


def lint(name, text):
    # The generator's own provenance notice legitimately names the source tier;
    # exclude it so the tier-path rule checks only real skill prose.
    text = re.sub(r"<!-- Generated by scripts/build-skills\.py from [^>]*?-->", "", text, count=1)
    problems = []
    for pat, msg in FORBIDDEN:
        m = pat.search(text)
        if m:
            problems.append(f"  {name}: {msg} -> {m.group(0)!r}")
    return problems


def strip_copy_notice(body):
    return re.sub(r"^\s*<!--\s*This file is a copy of.*?-->\s*\n", "", body, count=1, flags=re.S)


def render_skill(out_name, source_dir, scripts, owner_of, seam=None, fragment_text=None, source_label=None, scenario=""):
    """Return the rendered SKILL.md text for one skill."""
    raw = (source_dir / "SKILL.md").read_text(encoding="utf-8")
    fm, body = split_frontmatter(raw)
    fm = set_name(fm, out_name)
    body = strip_copy_notice(body)
    body = apply_seam(body, seam, fragment_text)
    if scripts:
        body = rewrite_script_paths(body, scripts, owner_of)
    fm = inject_spec_fields(fm, scenario, body, scripts)
    label = source_label or source_dir.relative_to(SKILLS).as_posix()
    notice = (f"<!-- Generated by scripts/build-skills.py from skills/{label}/SKILL.md — "
              f"do not edit this copy; edit the source and regenerate. -->\n")
    return f"---\n{fm}\n---\n\n{notice}\n{body.lstrip(chr(10))}"


def copy_aux(source_dir, dest_dir):
    """Copy a skill's templates/ (and any non-SKILL.md aux files) verbatim."""
    tmpl = source_dir / "templates"
    if tmpl.is_dir():
        shutil.copytree(tmpl, dest_dir / "templates", dirs_exist_ok=True)


def resolve_entry(manifest, scenario, skill, entry):
    """Resolve a manifest entry (handling combined `reuse`) to (source_dir, scripts, seam)."""
    if "reuse" in entry:
        base = manifest["scenarios"][entry["reuse"]][skill]
        source_dir = SKILLS / base["source"]
        scripts = list(base.get("scripts", []))
        seam = entry.get("seam")
        if seam:
            scripts += list(seam.get("scripts", []))
        return source_dir, scripts, seam, entry["reuse"]
    return SKILLS / entry["source"], list(entry.get("scripts", [])), entry.get("seam"), scenario


def owned_names(manifest):
    """Every skill name dobby's generator manages (across all scenarios). Anything
    NOT in this set — e.g. openspec-* installed by the OpenSpec CLI, or a project's
    own skills — is foreign and the generator must never touch it."""
    names = set(manifest["common"])
    for sc in manifest["scenarios"].values():
        names.update(sc.keys())
    return names


def assemble(manifest, scenario, dest_root):
    """Assemble one scenario into dest_root (a flat dir of skill folders).

    Non-destructive: only dobby-owned skill folders are written, and only
    dobby-owned folders that don't belong to this scenario are pruned. Foreign
    skill folders (openspec-*, a project's own skills) are left untouched.
    Returns lint problems (a non-empty list means nothing was written)."""
    owner_of = {s: meta["owner"] for s, meta in manifest["lib"].items()}
    problems = []
    rendered = {}   # name -> SKILL.md text
    sources = {}    # name -> source dir (for templates / aux files)
    used_scripts = {}  # script -> owner (collected for bundling)

    # 1. scenario-independent skills (verbatim, name = folder)
    for name in manifest["common"]:
        src = SKILLS / "_common" / name
        rendered[name] = render_skill(name, src, [], owner_of, source_label=f"_common/{name}", scenario=scenario)
        sources[name] = src

    # 2. scenario-specialized work-item skills
    for skill, entry in manifest["scenarios"][scenario].items():
        source_dir, scripts, seam, src_scenario = resolve_entry(manifest, scenario, skill, entry)
        fragment_text = None
        if seam:
            fragment_text = (SKILLS / seam["fragment"]).read_text(encoding="utf-8")
        rendered[skill] = render_skill(
            skill, source_dir, scripts, owner_of,
            seam=seam, fragment_text=fragment_text,
            source_label=source_dir.relative_to(SKILLS).as_posix(),
            scenario=scenario,
        )
        sources[skill] = source_dir
        for s in scripts:
            used_scripts[s] = owner_of[s]

    # 3. lint every rendered skill (after seam substitution + path rewrite):
    #    forbidden patterns in the full text, spec conformance on the frontmatter
    for name, text in rendered.items():
        problems += lint(name, text)
        fm, _ = split_frontmatter(text)
        problems += validate_frontmatter(name, fm)
    if problems:
        return problems

    dest_root.mkdir(parents=True, exist_ok=True)
    current = set(rendered)

    # 4. prune ONLY dobby-owned skills that don't belong to this scenario;
    #    never remove foreign folders (openspec-*, project skills).
    for name in owned_names(manifest) - current:
        stale = dest_root / name
        if stale.exists():
            shutil.rmtree(stale)

    # 5. write each owned skill into a clean per-skill folder (leaves siblings intact)
    for name, text in rendered.items():
        d = dest_root / name
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(text, encoding="utf-8", newline="\n")
        copy_aux(sources[name], d)

    # 6. bundle each used _lib script once, under its owner skill's scripts/
    for script, owner in used_scripts.items():
        owner_scripts = dest_root / owner / "scripts"
        owner_scripts.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SKILLS / "_lib" / script, owner_scripts / script)

    return []


def clean_skill_tree(path):
    """Fully reset a directory. Used only for the throwaway `build/` artifact —
    never for a real project's host dirs (see assemble's non-destructive writes)."""
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def cmd_build(args):
    manifest = load_manifest()
    out = Path(args.out)
    for scenario in SCENARIOS:
        dest = out / scenario
        clean_skill_tree(dest)
        problems = assemble(manifest, scenario, dest)
        if problems:
            print(f"[FAIL] lint failed for scenario '{scenario}':", file=sys.stderr)
            print("\n".join(problems), file=sys.stderr)
            return 1
        print(f"[ok] built {scenario} -> {dest.relative_to(REPO) if dest.is_relative_to(REPO) else dest}")
    return 0


def write_scenario_to_hosts(manifest, scenario, target_root):
    # Non-destructive: assemble() only manages dobby-owned skill folders under each
    # host dir, so anything already there (openspec-*, a project's own skills) survives.
    for host in HOSTS:
        dest = Path(target_root) / host
        problems = assemble(manifest, scenario, dest)
        if problems:
            print(f"[FAIL] lint failed assembling '{scenario}' into {dest}:", file=sys.stderr)
            print("\n".join(problems), file=sys.stderr)
            return 1
        print(f"[ok] wrote {scenario} -> {dest}")
    return 0


def print_openspec_hint(target):
    print()
    print("dobby does not bundle the OpenSpec workflow skills -- install them with the")
    print("OpenSpec CLI so they stay current and self-managed:")
    print(f"  cd {target}")
    print('  openspec init --tools "claude,github-copilot"')
    print("(dobby's non-destructive init leaves those skills untouched on re-runs.)")


def cmd_init(args):
    if args.scenario not in SCENARIOS:
        print(f"[FAIL] unknown scenario '{args.scenario}'. Choose one of: {', '.join(SCENARIOS)}", file=sys.stderr)
        return 2
    target = Path(args.target)
    if not target.is_dir():
        print(f"[FAIL] target project directory does not exist: {target}", file=sys.stderr)
        return 2
    code = write_scenario_to_hosts(load_manifest(), args.scenario, target)
    if code == 0:
        print_openspec_hint(target)
    return code


def cmd_dev(args):
    # dobby develops against the github flow (issues + PRs).
    return write_scenario_to_hosts(load_manifest(), "github", REPO)


def main(argv=None):
    p = argparse.ArgumentParser(prog="build-skills.py", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="mode", required=True)

    b = sub.add_parser("build", help="emit all three scenarios to a build dir")
    b.add_argument("--out", default=str(REPO / "build"))
    b.set_defaults(func=cmd_build)

    i = sub.add_parser("init", help="scaffold a scenario into a target project")
    i.add_argument("target", help="path to the target project root")
    i.add_argument("scenario", help=f"one of: {', '.join(SCENARIOS)}")
    i.set_defaults(func=cmd_init)

    d = sub.add_parser("dev", help="self-install the github scenario into this repo")
    d.set_defaults(func=cmd_dev)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
