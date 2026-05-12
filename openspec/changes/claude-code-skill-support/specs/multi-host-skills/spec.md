## ADDED Requirements

### Requirement: One canonical skills folder SHALL be the source of truth

The repository SHALL contain a top-level `skills/` directory. Each skill (dobby skills, openspec workflow skills, `grill-me`, and any future skills) SHALL exist as one folder inside `skills/`, containing its `SKILL.md`, any helper scripts under `scripts/`, and any templates under `templates/`.

#### Scenario: Contributor edits a skill
- **WHEN** a contributor makes any change to a skill's instructions, helper scripts, or templates
- **THEN** they SHALL make the change inside `skills/<skill-name>/`, not in any of the host-discovery copies

#### Scenario: New skill is added
- **WHEN** a contributor adds a new skill
- **THEN** the canonical folder SHALL be created under `skills/<new-skill-name>/`
- **AND** the sync script SHALL be run to populate the host-discovery copies

### Requirement: Skills SHALL be discoverable from both Copilot CLI and Claude Code

The repository SHALL contain copies of every canonical skill folder at both:
- `.github/skills/<skill-name>/` — for GitHub Copilot CLI discovery
- `.claude/skills/<skill-name>/` — for Claude Code discovery

These copies SHALL be checked into git so that any contributor cloning the repository can use the skills immediately from either host without running setup steps.

#### Scenario: Copilot CLI lists every skill
- **WHEN** a Copilot CLI session is started in a clone of the repository
- **THEN** every skill present under `skills/` SHALL be listed as invokable, with prerequisites identical to those declared by the canonical source

#### Scenario: Claude Code lists every skill
- **WHEN** a Claude Code session is started in a clone of the repository
- **THEN** every skill present under `skills/` SHALL be listed as invokable, with prerequisites identical to those declared by the canonical source

### Requirement: Host-discovery copies SHALL declare themselves as copies

Every SKILL.md file under `.github/skills/<name>/` and `.claude/skills/<name>/` SHALL include, within the first 10 lines following its YAML frontmatter, a notice that it is a copy of `skills/<name>/SKILL.md` and that edits SHALL be made to the canonical source.

#### Scenario: Contributor opens a host-discovery copy
- **WHEN** a contributor opens any SKILL.md under `.github/skills/` or `.claude/skills/`
- **THEN** the file SHALL contain a visible "copy of skills/<name>/SKILL.md — edit the source, not this copy" notice near the top

### Requirement: A sync script SHALL copy the canonical source to both host paths

The repository SHALL provide `scripts/sync-skills.py` that, when run, makes the contents of `.github/skills/<name>/` and `.claude/skills/<name>/` exactly match `skills/<name>/` for every skill, modulo the prepended "do not edit" notice. The script SHALL use only the Python standard library.

#### Scenario: Sync after editing a skill
- **WHEN** a contributor edits any file under `skills/<name>/` and runs `python scripts/sync-skills.py`
- **THEN** both `.github/skills/<name>/` and `.claude/skills/<name>/` SHALL reflect the change
- **AND** any files that exist in a host-copy but not in the canonical source SHALL be removed from the host-copy

#### Scenario: Sync after deleting a skill
- **WHEN** a contributor removes a folder under `skills/` and runs the sync script
- **THEN** the corresponding folders under `.github/skills/` and `.claude/skills/` SHALL be removed

### Requirement: A check script SHALL detect drift

The repository SHALL provide `scripts/check-skill-sync.py` that exits non-zero when any file under `.github/skills/` or `.claude/skills/` differs from what the sync script would produce. The output SHALL identify each drifted file and SHALL include the exact command to fix it. The script SHALL use only the Python standard library.

#### Scenario: All copies are in sync
- **WHEN** the check script runs against a tree where every host-discovery copy matches the canonical source
- **THEN** the script SHALL exit 0 and SHALL print a one-line confirmation

#### Scenario: A host copy is hand-edited
- **WHEN** a contributor edits a SKILL.md under `.github/skills/` or `.claude/skills/` directly and runs the check script
- **THEN** the script SHALL exit non-zero
- **AND** the failure message SHALL name the drifted file(s) and SHALL state that the contributor must move their changes into `skills/<name>/` and re-run the sync

### Requirement: Helper-script invocations in SKILL.md SHALL use the canonical path

Where a SKILL.md body invokes a helper Python script, the documented invocation SHALL refer to the script by its canonical path (`skills/<name>/scripts/<script>.py`), not by a host-specific copy path. This holds for both the canonical SKILL.md and the host-discovery copies (because the copies are byte-for-byte copies of the source apart from the "do not edit" notice).

#### Scenario: A skill invokes a helper script
- **WHEN** any SKILL.md in the repository documents how to invoke a helper script
- **THEN** the documented invocation SHALL use the path `skills/<name>/scripts/<script>.py`

### Requirement: README.md SHALL document every skill

`README.md` SHALL include a catalog of all skills. For each skill the catalog SHALL state:

1. The skill's name.
2. A one-line description.
3. Which host(s) it runs on (Copilot CLI, Claude Code, or both).
4. Its prerequisites (e.g., `az` CLI with the `azure-devops` extension, Python 3, `openspec` CLI).
5. At least one usage example.
6. A link to the canonical source folder under `skills/`.

#### Scenario: A user reads the README
- **WHEN** a user reads `README.md`
- **THEN** every skill present under `skills/` SHALL appear in the catalog
- **AND** the catalog SHALL accurately state which host(s) each skill supports

#### Scenario: A new skill is added
- **WHEN** a contributor adds a new skill
- **THEN** the same change SHALL include the catalog entry for that skill in `README.md`

### Requirement: Host-instruction files SHALL describe the layout and sync rule

`CLAUDE.md` and `.github/copilot-instructions.md` SHALL each contain a "Skill layout" section that explains:

1. `skills/<name>/` is the canonical source.
2. `.github/skills/` and `.claude/skills/` are copies for in-repo host discovery and are not edited directly.
3. The sync and check commands.

#### Scenario: A contributor reads either instruction file
- **WHEN** a contributor reads `CLAUDE.md` or `.github/copilot-instructions.md`
- **THEN** they SHALL find clear directions on which folder to edit and how to keep the copies in sync

### Requirement: Host-specific tuning SHALL be inline and rare

When a skill must call out a difference between Copilot CLI and Claude Code (e.g., a tool that exists under different names, a slash-command syntax difference), the difference SHALL be noted inline in the canonical SKILL.md in a single sentence or short paragraph. No generator, template, or per-host file SHALL be required for these notes.

#### Scenario: A skill mentions a host-specific tool name
- **WHEN** a skill needs to refer to a built-in tool whose name differs between hosts
- **THEN** the canonical SKILL.md SHALL mention both names inline and the host-copies SHALL inherit that mention via the standard sync

### Requirement: Existing Copilot users SHALL see no behavior change

After this change is applied, invoking any skill from Copilot CLI SHALL behave identically to its pre-change behavior, apart from the documented helper-script paths (which are internal to the skill and not a user-facing contract).

#### Scenario: Copilot user invokes dobby-create-pbi after migration
- **WHEN** a user invokes `dobby-create-pbi` from Copilot CLI on the post-migration repository
- **THEN** the skill SHALL collect the same fields, validate the same prerequisites, and produce the same Azure DevOps work item as before
- **AND** the helper-script paths SHALL resolve correctly without manual intervention
