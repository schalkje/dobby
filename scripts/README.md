# scripts/

Repository-level helper scripts. Python stdlib only — no pip install required.

## Skill generation

Dobby skills are **assembled per scenario at build time** rather than routed at runtime. The sources live in three tiers under `skills/`, and a generator (`build-skills.py`) produces a flat, scenario-specialized skill set with no dispatcher and no runtime `backend` branching.

### Source layout

| Path | Role |
|---|---|
| `skills/_lib/` | Shared helper scripts (`azdo-*.py`, `evidence-store.py`), authored once; bundled into a scenario only when used. |
| `skills/_common/` | Scenario-independent, dobby-authored skills (`grill-*`, `dobby-worktree`); copied into **every** scenario. (The `openspec-*` skills are **not** here — they're installed per-project by the OpenSpec CLI.) |
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

After assembling each `SKILL.md`, the generator runs a **forbidden-pattern lint** (template/macro syntax, leftover seam anchors, references to retired `dobby-ado-*`/`dobby-gh-*` skills, dispatcher/backend-routing prose) and **fails the build** if any appear — so the "flat, no-template" guarantees are self-enforcing.

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
  // Mirrors the old azdo-defaults.json.
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
    "owner": "vanlanschot",
    "repo": "strada",
    "defaultLabels": ["needs-triage"],
    "projectNumber": 7
  },

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

For `"ado"` or `"github"` backends, only the active backend's block is required. For `"combined"`, both `ado` and `github` blocks must be populated. The `worktree` block is optional for any backend.

### `migrate-dobby-config.py`

One-time migration from the legacy `.dobby/azdo-defaults.json` to the new `.dobby/config.json`. Reads the legacy file, wraps its contents in `{ "backend": "ado", "ado": <legacy> }`, writes the new file, and removes the legacy file only after the new file is written successfully.

```bash
python scripts/migrate-dobby-config.py              # migrate this project
python scripts/migrate-dobby-config.py --dry-run    # print result, don't write
python scripts/migrate-dobby-config.py --force      # allow overwriting existing config.json
```

Idempotent — safe to re-run. If `.dobby/config.json` already exists the script exits 0 with an "already migrated" message and changes nothing. If neither file exists (a fresh checkout) the script exits 0 without doing anything.

Run it manually in any project that still has the legacy `.dobby/azdo-defaults.json`.

## Why these scripts exist

Symlinks would work on macOS/Linux but are fragile on Windows (the primary dev OS for this repo) and aren't always preserved by git. A small copy-and-check pair is cross-platform and gives a clear failure mode (the check script names the drifted file).
