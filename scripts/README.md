# scripts/

Repository-level helper scripts. Python stdlib only — no pip install required.

## Skill generation

Dobby skills are **assembled per scenario at build time** rather than routed at runtime. The sources live in three tiers under `skills/`, and a generator (`build-skills.py`) produces a flat, scenario-specialized skill set with no dispatcher and no runtime `backend` branching.

### Source layout

| Path | Role |
|---|---|
| `skills/_lib/` | Shared helper scripts (`azdo-*.py`), authored once; bundled into a scenario only when used. |
| `skills/_common/` | Scenario-independent, dobby-authored skills (`grill-*`, `dobby-worktree`); copied into **every** scenario. (The `openspec-*` skills are **not** here — they're installed per-project by the OpenSpec CLI.) |
| `skills/_fragments/` | Shared prose fragments, authored once and woven into any source SKILL.md at build time via `<!-- dobby:include:NAME -->` anchors (see below). |
| `skills/ado/` | ADO-specialized skill prose, under the user-facing names (`dobby-{create,update,propose,close,implement}-pbi`). |
| `skills/github/` | GitHub-specialized skill prose, same user-facing names. |
| `skills/combined/` | Only the skills that genuinely span both backends (`dobby-close-pbi`), plus `_fragments/` woven into reused sources. |
| `skills/manifest.json` | The assembly contract (see below). |

Generated copies land in `.claude/skills/` (Claude Code) and `.github/skills/` (GitHub Copilot CLI). **Do not edit generated copies** — edit the source tier and regenerate.

### `skills/manifest.json`

A single, stdlib-parseable manifest declares, per scenario, how each user-facing skill is assembled:

- `userFacingSkills` / `common` — the five work-item skills and the scenario-independent skills.
- `lib.<script>.owner` — which skill physically owns each shared script in the output. The script is bundled **once** into that owner's `scripts/` dir; other skills that use it reference the owner's path. (De-duped by name — preserves today's shared-by-reference pattern.)
- `scenarios.<scenario>.<skill>` — one of:
  - `{ "source": "<tier>/<skill>", "scripts": [...] }` — assemble from this source file, bundling the listed `_lib` scripts.
  - `{ "reuse": "<other-scenario>" }` — reuse another scenario's assembled skill verbatim (used by `combined` for create/update/propose, which reuse `ado`).
  - `{ "reuse": "github", "seam": { "anchor": "...", "fragment": "...", "scripts": [...] } }` — reuse a source and substitute a named source anchor with a prose fragment (used by `combined`'s `implement-pbi` to weave in the ADO PBI→PR link step). The anchor is stripped from every other scenario, so generated output never contains it.

### `skills/_fragments/` (includes)

Prose that recurs across skills (prerequisite checks, `.dobby/config.json` examples, the
ADO dev-links instructions, command-execution rules) is authored **once** as a fragment under
`skills/_fragments/<name>.md`. Any source SKILL.md — and the combined seam fragment — can pull it
in with an anchor line:

```markdown
<!-- dobby:include:ado-prereqs -->
```

At build time the generator replaces the anchor with the fragment's content, so generated output
stays flat and self-contained while sources never duplicate the prose. Rules:

- **No nesting** — a fragment cannot include another fragment. (The combined seam fragment may use
  includes because the seam is substituted *before* includes are applied.)
- Fragments may reference `skills/_lib/<script>.py` paths; the generator rewrites them per skill to
  the bundled `<owner-skill>/scripts/<script>` location, exactly as it does in SKILL.md prose.
- A missing fragment is a **build failure**: the anchor is left in place and the
  `dobby:include:` lint rule names it.

Skill folders may also carry `templates/`, `references/`, and `evals/` directories — all three are
bundled verbatim into the generated skill alongside `SKILL.md` (`references/` holds
progressive-disclosure detail the SKILL.md points to; keep references one level deep).

### `build-skills.py`

The generator. Stdlib only. Three modes:

```bash
python scripts/build-skills.py build [--out build]   # emit all 3 scenarios to build/<scenario>/ (gitignored)
python scripts/build-skills.py init <target> <scenario>  # scaffold a scenario into a target project's .claude + .github
python scripts/build-skills.py dev                   # self-install the github scenario into dobby's own .claude + .github
```

**Non-destructive.** `init` and `dev` manage only the skill folders dobby owns (the manifest's `common` + each scenario's keys). Foreign folders — the `openspec-*` skills, or a project's own — are left untouched, so it's safe to re-run `init` on a project that already has other skills. (Only `build/` is fully reset each run.)

**OpenSpec skills are not bundled.** dobby ships only its own skills. The `openspec-*` workflow skills are installed per-project with the OpenSpec CLI, which writes them straight into `.claude/skills/` and `.github/skills/`:

```bash
openspec init --tools "claude,github-copilot"   # run in the target project; quote the list
```

`build-skills.py init` prints this reminder; `dobby.ps1 init` can run it for you (`-OpenSpec`). Keep them current with `openspec update`. In this repo the generated `openspec-*` skill folders are gitignored.

**Convenience wrapper — `dobby.ps1` (repo root).** On Windows/PowerShell you can drive all of the above through `dobby.ps1` instead of remembering the `python` invocations. It finds Python for you and resolves paths against its own location, so it works from any directory:

```powershell
.\dobby.ps1 init [<target>] [<scenario>]   # scaffold a scenario (prompts when args are omitted)
.\dobby.ps1 dev                            # regenerate dobby's own host copies (github scenario)
.\dobby.ps1 build [--out <dir>]            # emit all three scenarios to build/<scenario>/
.\dobby.ps1 check                          # run check-skill-sync.py
.\dobby.ps1 help                           # usage
```

`init` also offers to (a) drop a `.dobby/config.json` skeleton for the chosen scenario and (b) run `openspec init` in the target to install the OpenSpec workflow skills. Drive both without prompts for scripting: `-Config` / `-NoConfig` (and `-Force` to overwrite an existing config), `-OpenSpec` / `-NoOpenSpec`. Example: `.\dobby.ps1 init ..\my-app github -Config -OpenSpec`.

After assembling each `SKILL.md`, the generator runs a **forbidden-pattern lint** (template/macro syntax, leftover seam anchors, references to retired `dobby-ado-*`/`dobby-gh-*` skills, dispatcher/backend-routing prose, host-specific `.github/skills//.claude/skills/` paths, source-tier `skills/<tier>/` paths, backslash paths) and a **spec-conformance check** on the frontmatter (only portable [Agent Skills spec](https://agentskills.io/specification) keys; name/description/compatibility constraints; name must match the directory), and **fails the build** if any appear — so the "flat, no-template, portable" guarantees are self-enforcing.

The generator also **injects spec fields** into every generated skill: a `compatibility:` line computed from what the prose actually invokes (az/gh/python/openspec/git-worktree), and `scenario` + `generator` provenance merged into the source's `metadata:` block (source-authored keys win). `GENERATOR_VERSION` in `build-skills.py` is deliberately a manually bumped constant, not a git SHA — `check-skill-sync.py` regenerates and diffs, so the stamp must be stable across commits.

Dobby develops against the **github** flow (issues + PRs): its committed `.claude/skills/` and `.github/skills/` are the `dev` output. Run `dev` and commit the result after editing any github-scenario or `_common` source.

### `check-skill-sync.py`

Assembles the github scenario into a temp directory and diffs it against the committed `.claude/skills/` and `.github/skills/`. Exits 0 if they match; exits non-zero with the drifted files and the exact fix command (`python scripts/build-skills.py dev`).

```bash
python scripts/check-skill-sync.py
```

Use this to verify a clean tree before pushing (or as a pre-commit hook — none is installed by default).

## Project tracker config

Generated skills read `.dobby/config.json` for the per-backend connection details. The shape is:

```jsonc
{
  // Records which scenario this project's skills were generated for
  // ("ado", "github", or "combined"). RETAINED but DEMOTED: it is no
  // longer read at skill-invocation time to route — skills are already
  // scenario-specialized at generation time. "combined" = ADO work items
  // + GitHub repo/PRs.
  "backend": "ado",

  // Populated when backend = "ado" or "combined".
  "ado": {
    "organization": "https://dev.azure.com/myorg/",
    "project": "MyProject",
    "team": "MyTeam",
    "devLinks": {
      "repoReachableFromAdo": true,
      "host": "github",
      "githubConnectionId": "<guid>",
      "adoProjectId": "<guid>",
      "adoRepoId": "<guid>"
    }
  },

  // Populated when backend = "github" or "combined".
  "github": {
    "owner": "myorg",
    "repo": "my-repo",
    "defaultLabels": ["needs-triage"],
    "projectNumber": 7
  },

  // Optional. Free-form reminders that `dobby-implement-pbi` reads at the
  // start of a run and repeats back to the user (e.g. "run the linter before
  // committing", "never push directly to main").
  "userReminders": [
    "<reminder text>"
  ],

  // Optional. Controls git-worktree-based parallel development.
  // When enabled, each PBI gets its own worktree directory instead
  // of using `git checkout -b`.
  "worktree": {
    "enabled": false,
    // Custom worktree root. Default: <repo-parent>/<repo-name>-worktrees/
    "root": "../my-repo-worktrees"
  }
}
```

For `"ado"` or `"github"` backends, only the active backend's block is required. For `"combined"`, both `ado` and `github` blocks must be populated. The `worktree` and `userReminders` blocks are optional for any backend.

## Skill evals

Skills are tested like code: each tested skill carries an `evals/evals.json` next to its source (bundled into generated output by the generator). The file holds:

- `description_tuning.should_trigger` / `should_not_trigger` — prompts for measuring whether the skill's description fires at the right moments (over-triggering is as real a failure as under-triggering).
- `evals[]` — scenarios run in a **fresh** session with the skill installed, graded against `expected` (must observe) and `forbidden` (must not observe) behavior lists. Required keys per eval: `id`, `kind` (`behavior` or `pressure`), `scenario`, `setup`, `expected`, `forbidden`. Every skill needs ≥3 evals including ≥1 `pressure` eval — a scenario that actively tempts the agent to break a discipline rule (never auto-retry creation, never `gh issue close`, …).

```bash
python scripts/run-skill-evals.py --validate          # schema check (runs in CI)
python scripts/run-skill-evals.py --list              # summary of all evals
python scripts/run-skill-evals.py --run-sheet out.md  # manual grading checklist
```

Running the sessions and grading is model-in-the-loop and deliberately not automated here; use the run sheet by hand, or the `skill-creator` plugin's eval harness for automated grading. **When you edit a skill that has evals, re-run its evals before committing** — write the skill change like a TDD cycle: capture the failure first (run the scenario without the change), then make the minimal edit that fixes it.

## Why these scripts exist

Symlinks would work on macOS/Linux but are fragile on Windows (the primary dev OS for this repo) and aren't always preserved by git. A small copy-and-check pair is cross-platform and gives a clear failure mode (the check script names the drifted file).
