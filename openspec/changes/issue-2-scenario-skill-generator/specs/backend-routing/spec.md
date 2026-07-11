## MODIFIED Requirements

### Requirement: Project tracker configuration file
The system SHALL read project-level tracker configuration from `.dobby/config.json` in the repository root. The file SHALL contain a top-level `backend` field whose value is `"ado"`, `"github"`, or `"combined"`, and per-backend sub-objects (`ado`, `github`) containing connection details for the selected scenario. The `backend` field SHALL be treated as a **record of which scenario the project's skills were generated for**; it SHALL NOT be read at skill-invocation time to route between backend implementations (skills are already scenario-specialized at generation time).

#### Scenario: Config records the generated scenario
- **WHEN** `.dobby/config.json` exists and contains `{ "backend": "ado", "ado": { ... } }`
- **THEN** the value `"ado"` SHALL be interpreted as a record that this project was generated for the ADO scenario
- **AND** no skill SHALL read `backend` to decide which backend `SKILL.md` to follow at invocation

#### Scenario: Connection details remain per-project
- **WHEN** a generated, scenario-specialized skill needs connection details (organization/project/team for ADO, owner/repo for GitHub)
- **THEN** it SHALL read them from the corresponding `ado` or `github` block of `.dobby/config.json`

#### Scenario: Combined scenario is a valid recorded value
- **WHEN** `.dobby/config.json` contains `{ "backend": "combined", "ado": { ... }, "github": { ... } }`
- **THEN** `"combined"` SHALL be accepted as a valid recorded scenario value

## REMOVED Requirements

### Requirement: Interactive backend selection on first run
**Reason**: Scenario selection moves from skill-invocation time to skill-generation time. The build-time CLI (`scripts/build-skills.py`, `init` mode) asks for the scenario when scaffolding a project; shipped skills no longer prompt for or persist a backend selector at runtime.
**Migration**: Choose the scenario when generating skills via `scripts/build-skills.py init <target> <scenario>`. The `backend` value in `.dobby/config.json` is retained as a record of that choice (see the modified "Project tracker configuration file" requirement).

### Requirement: Dispatcher hands off to backend implementation
**Reason**: The runtime dispatcher + nested-backend architecture is replaced by build-time assembly. Each user-facing skill (`dobby-create-pbi`, `dobby-close-pbi`, `dobby-propose-from-pbi`, etc.) is generated already specialized for the project's scenario, so there is no dispatcher and no nested `SKILL.md` read.
**Migration**: Generate the scenario's flat skills with `scripts/build-skills.py`. The user-facing skill names are preserved, so existing intents and muscle memory continue to work; only the implementation behind them (flat vs dispatched) changes.

### Requirement: Skill description discipline prevents picker collision
**Reason**: With a flat, scenario-specialized skill set there is no dispatcher/backend pair to disambiguate, so the "preferred match vs internal" description discipline is no longer needed. Each user-facing skill is the single match for its intent.
**Migration**: Generated skills carry their user-facing name and description directly; backend-named "internal" skills are no longer shipped.
