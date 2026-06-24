# Contributing to Dobby

How to add, modify, and maintain skills in this library.

## Adding a new skill

### Step 1: Create the canonical folder

```
skills/<skill-name>/
├── SKILL.md              # Required
├── templates/            # Optional — if the skill generates structured content
└── scripts/              # Optional — if CLI tools have limitations to work around
```

### Step 2: Write the SKILL.md

Start with YAML frontmatter:

```yaml
---
name: <skill-name>
description: <one-line description — this is what host discovery uses for intent matching>
---
```

Then write the prompt body. Refer to [Skill Anatomy](skill-anatomy.md) for the four patterns (dispatcher, backend, wrapper, conversational).

### Step 3: Sync to host directories

```bash
python scripts/sync-skills.py           # regenerate .github/skills/ and .claude/skills/
python scripts/check-skill-sync.py      # verify no drift (exits non-zero on drift)
```

**Always run both before committing.** The sync script copies your canonical skill to both host directories and injects a "do not edit" notice into the generated copies.

### Step 4: Update README.md

Add the new skill to the skill catalog in `README.md` following the existing format.

## Modifying an existing skill

1. **Edit only under `skills/<name>/`** — never edit `.github/skills/` or `.claude/skills/` directly
2. Run `sync-skills.py` + `check-skill-sync.py`
3. If you changed behavior significantly, manually invoke the skill to verify

## Adding a tracker backend skill

Backend skills are internal (invoked by dispatchers). Follow these additional rules:

- **Identity first** — run `az account show` or `gh auth status` early
- **Own your connection details** — collect and persist to `.dobby/config.json`
- **Use JSON output** — `--output json` / `--json` on every CLI call
- **Never auto-retry creation** — prevents duplicate work items
- **Trust user values** — attempt operations first, re-prompt only on failure

### Adding an ADO helper script

If the `az` CLI can't do what you need:

1. Create the script under `skills/<skill-name>/scripts/`
2. Use Python 3 stdlib only (no pip dependencies)
3. Implement `--help` for self-documentation
4. Use the auth fallback chain: `AZURE_DEVOPS_EXT_PAT` → `ADO_TOKEN` → `az account get-access-token`
5. Add retry-with-backoff for HTTP 429/502/503/504
6. Output JSON for reliable parsing

## Adding a conversational skill variation

See [Conversational Skills](conversational-skills.md) for the framework and template. Key points:

1. Create as a separate skill (`skills/<variation-name>/`)
2. Define focus area, question priorities, exit criteria
3. Keep it standalone — no tracker/CLI dependencies in the skill itself

## Naming conventions

| Type | Pattern |
|---|---|
| Public dispatcher | `dobby-<verb>-pbi` |
| ADO backend | `dobby-ado-<verb>-pbi` |
| GitHub backend | `dobby-gh-<verb>-issue` |
| OpenSpec wrapper | `openspec-<verb>` |
| Conversational | descriptive name (e.g., `grill-me`) |

## Validation checklist

Before committing any skill change:

- [ ] Edited only under `skills/<name>/` (not `.github/skills/` or `.claude/skills/`)
- [ ] Ran `python scripts/sync-skills.py`
- [ ] Ran `python scripts/check-skill-sync.py` — exits clean
- [ ] Updated `README.md` if adding a new skill
- [ ] Manually invoked the skill if behavior changed
- [ ] Commit includes `Co-authored-by: Copilot` trailer

## What NOT to do

| Don't | Why |
|---|---|
| Edit `.github/skills/` or `.claude/skills/` directly | These are generated — edits will be overwritten |
| Add backend-specific behavior to dispatchers | Dispatchers only route; backends own all API calls |
| Store credentials in `.dobby/config.json` | Config stores connection details, not secrets |
| Assume ADO and GitHub work the same way | Each backend follows its tracker's native idiom |
| Put variation behavior inside an existing skill | Variations are separate skills with their own SKILL.md |
| Add pip dependencies to helper scripts | All Python helpers use stdlib only |
| Commit anything from `.dobby/evidence/` | May contain sensitive screenshots — it's gitignored |
