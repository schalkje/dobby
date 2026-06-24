## ADDED Requirements

### Requirement: Build-time CLI assembler

The system SHALL provide a command-line tool (`scripts/build-skills.py`, Python standard library only) that assembles flat, scenario-specialized skill sets from per-scenario source files. The tool SHALL support three output modes — `build`, `init`, and `dev` — and SHALL NOT require any third-party dependency or templating engine.

#### Scenario: Tool runs with stdlib only
- **WHEN** `scripts/build-skills.py` is executed in an environment with only Python 3 and its standard library installed
- **THEN** the tool SHALL run to completion without importing any third-party package

#### Scenario: Unknown mode is rejected
- **WHEN** the tool is invoked with a mode that is not `build`, `init`, or `dev`
- **THEN** the tool SHALL exit non-zero and print usage describing the three valid modes

### Requirement: Flat scenario output with no runtime dispatch

Given a chosen scenario and the per-scenario sources, the assembler SHALL produce a skill set under the user-facing names (`dobby-create-pbi`, `dobby-update-pbi`, `dobby-propose-from-pbi`, `dobby-close-pbi`, `dobby-implement-pbi`, plus scenario-independent skills) in which no skill is a dispatcher, no skill reads a nested backend `SKILL.md` at invocation, and no skill branches on a `.dobby/config.json` `backend` value.

#### Scenario: Generated skill set has no dispatcher
- **WHEN** the assembler produces a scenario's skills
- **THEN** the output SHALL contain exactly one `SKILL.md` per user-facing skill name
- **AND** no generated `SKILL.md` SHALL instruct the reader to read another skill's `SKILL.md` to resolve a backend
- **AND** no generated `SKILL.md` SHALL contain `backend`-value branching logic for routing

#### Scenario: Generated prose contains no template syntax
- **WHEN** any generated `SKILL.md` is inspected
- **THEN** it SHALL read as plain prose containing no template placeholders, conditional directives, or macro syntax

### Requirement: Three-tier source layout

The repository SHALL organize skill sources into three tiers under `skills/`: `_lib/` for shared helper scripts authored once, `_common/` for scenario-independent skills copied into every scenario, and scenario folders (`ado/`, `github/`, `combined/`) for scenario-specialized skill prose under user-facing names.

#### Scenario: Scenario-independent skill comes from _common
- **WHEN** the assembler builds any scenario
- **THEN** each scenario-independent skill (the `openspec-*` workflow skills, the `grill-*` skills, and `dobby-worktree`) SHALL be sourced from `skills/_common/` and appear in every scenario's output

#### Scenario: Specialized prose comes from the scenario folder
- **WHEN** the assembler builds the `ado` (or `github`) scenario
- **THEN** each backend-specialized skill SHALL be sourced from `skills/ado/` (or `skills/github/`) under its user-facing name

### Requirement: Per-scenario manifest declares assembly and reuse

The system SHALL provide a declarative, stdlib-parseable manifest that maps, for each scenario, each user-facing skill name to its source file and the `_lib` scripts it bundles. Reuse across scenarios SHALL be expressed explicitly in the manifest rather than inferred.

#### Scenario: Manifest names source and scripts per skill
- **WHEN** the assembler builds a skill for a scenario
- **THEN** it SHALL consult the manifest to determine which source folder's file provides that skill and which `_lib` scripts to bundle with it

#### Scenario: Combined scenario reuse is explicit
- **WHEN** the assembler builds the `combined` scenario
- **THEN** the manifest SHALL declare that `create-pbi`, `update-pbi`, and `propose-from-pbi` reuse the `ado` sources
- **AND** that `implement-pbi` reuses the `github` source plus the ADO PBI→PR link step
- **AND** that `close-pbi` uses the `combined`-specific source file

### Requirement: Shared scripts bundled once per scenario

When a scenario's skills reference an `_lib` helper script, the assembler SHALL bundle that script exactly once in the scenario output (de-duplicated by script name) and the generated prose SHALL reference that single copy — preserving the shared-by-reference pattern rather than forking a copy per referencing skill.

#### Scenario: A shared ADO script is not duplicated
- **WHEN** the assembler builds a scenario whose `create`, `update`, `propose`, and `close` skills all reference `azdo-update-fields.py`
- **THEN** the script SHALL appear exactly once in the scenario output
- **AND** each generated skill that uses it SHALL reference that one bundled path

### Requirement: build mode emits all scenarios to a gitignored build directory

In `build` mode the assembler SHALL emit all three scenarios to `build/<scenario>/`, and the `build/` directory SHALL be gitignored.

#### Scenario: build mode produces all scenarios
- **WHEN** the tool is run in `build` mode
- **THEN** `build/ado/`, `build/github/`, and `build/combined/` SHALL each contain that scenario's flat skill set
- **AND** `build/` SHALL be listed in `.gitignore` so the artifact is not committed

### Requirement: init mode scaffolds a scenario into a target project

In `init` mode the assembler SHALL, given a target project path and a chosen scenario, write that scenario's skills into the target project's `.claude/skills/` and `.github/skills/` directories.

#### Scenario: init writes scenario skills to a target project
- **WHEN** the tool is run in `init` mode with a target project path and a chosen scenario
- **THEN** the scenario's skills SHALL be written under the target project's `.claude/skills/` and `.github/skills/`
- **AND** the written skills SHALL be the flat, dispatcher-free set for that scenario

### Requirement: dev mode self-installs the github scenario into dobby

In `dev` mode (self-install), run within the dobby repository, the assembler SHALL write the **github** scenario into dobby's own `.claude/skills/` and `.github/skills/` directories. These generated copies are committed to the dobby repository, replacing the role previously served by `sync-skills.py`.

#### Scenario: dev mode regenerates dobby's committed host copies
- **WHEN** the tool is run in `dev` mode inside the dobby repo
- **THEN** dobby's own `.claude/skills/` and `.github/skills/` SHALL contain the **github** scenario's flat skill set
- **AND** each generated `SKILL.md` SHALL carry a notice that it is generated from `skills/<scenario>/<skill>/SKILL.md` and SHALL NOT be edited directly
