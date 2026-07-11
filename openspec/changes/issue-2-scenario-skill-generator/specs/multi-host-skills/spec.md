## MODIFIED Requirements

### Requirement: One canonical skills folder SHALL be the source of truth

The repository SHALL keep skill sources under `skills/`, organized into the three-tier layout: `skills/_lib/` (shared helper scripts), `skills/_common/` (scenario-independent skills), and scenario folders (`skills/ado/`, `skills/github/`, `skills/combined/`) for scenario-specialized skill prose under user-facing names. Contributors SHALL edit these sources, never the generated host-discovery copies.

#### Scenario: Contributor edits a skill
- **WHEN** a contributor changes a skill's instructions, helper scripts, or templates
- **THEN** they SHALL make the change inside the appropriate `skills/` source tier (`_lib`, `_common`, or a scenario folder), not in any generated host-discovery copy

#### Scenario: New skill is added
- **WHEN** a contributor adds a new skill
- **THEN** the source SHALL be created under the appropriate `skills/` tier and listed in the per-scenario manifest
- **AND** the generator SHALL be run to populate the host-discovery copies

### Requirement: A sync script SHALL copy the canonical source to both host paths

The repository SHALL provide a build-time generator (`scripts/build-skills.py`) whose `dev` mode assembles the **github** scenario into dobby's own `.claude/skills/` and `.github/skills/`, replacing the previous blind-mirror `scripts/sync-skills.py`. The generator SHALL use only the Python standard library and SHALL produce a flat, scenario-specialized skill set (no dispatcher, no nested backend skills).

#### Scenario: Regenerate host copies after editing a skill
- **WHEN** a contributor edits a github-scenario or `_common` source and runs `scripts/build-skills.py` in `dev` mode
- **THEN** dobby's `.claude/skills/` and `.github/skills/` SHALL reflect the change
- **AND** any generated file that no longer corresponds to a source SHALL be removed from the host copies

#### Scenario: Legacy mirror script is retired
- **WHEN** the new generator is in place
- **THEN** `scripts/sync-skills.py` SHALL be removed
- **AND** repository documentation SHALL reference the generator's `dev` mode instead

### Requirement: A check script SHALL detect drift

The repository SHALL provide `scripts/check-skill-sync.py` that exits non-zero when dobby's committed `.claude/skills/` or `.github/skills/` differ from what the generator's `dev` (github-scenario) assembly would produce. The output SHALL identify each drifted file and SHALL include the exact command to fix it. The script SHALL use only the Python standard library.

#### Scenario: Committed copies match the generated github scenario
- **WHEN** the check script runs against a tree where the committed host copies match the generator's `dev` output
- **THEN** the script SHALL exit 0 and SHALL print a one-line confirmation

#### Scenario: A host copy is stale or hand-edited
- **WHEN** a committed host copy differs from the generator's `dev` output (because a source changed without regeneration, or a copy was hand-edited)
- **THEN** the script SHALL exit non-zero
- **AND** the failure message SHALL name the drifted file(s) and SHALL state the exact `build-skills.py` command to regenerate them

### Requirement: Host-instruction files SHALL describe the layout and sync rule

`CLAUDE.md` and `.github/copilot-instructions.md` SHALL each contain a section that explains:

1. The three-tier `skills/` source layout (`_lib`, `_common`, scenario folders) and the per-scenario manifest.
2. That `.github/skills/` and `.claude/skills/` are generated copies (the github scenario) for in-repo host discovery and are not edited directly.
3. The generator commands (`build`, `init`, `dev`) and the check command.

#### Scenario: A contributor reads either instruction file
- **WHEN** a contributor reads `CLAUDE.md` or `.github/copilot-instructions.md`
- **THEN** they SHALL find clear directions on which source tier to edit, how the scenarios are assembled, and how to regenerate and verify the committed copies
