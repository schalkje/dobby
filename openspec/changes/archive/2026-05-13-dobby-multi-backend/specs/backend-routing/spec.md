## ADDED Requirements

### Requirement: Project tracker configuration file
The system SHALL read project-level tracker configuration from `.dobby/config.json` in the repository root. The file SHALL contain a top-level `backend` field whose value is either `"ado"` or `"github"`, and per-backend sub-objects (`ado`, `github`) containing connection details for the selected backend.

#### Scenario: Config file present with valid backend
- **WHEN** `.dobby/config.json` exists and contains `{ "backend": "ado", "ado": { ... } }`
- **THEN** any dobby dispatcher skill SHALL read the file, accept `"ado"` as the active backend, and proceed to route to the corresponding backend implementation

#### Scenario: Config file present with valid github backend
- **WHEN** `.dobby/config.json` exists and contains `{ "backend": "github", "github": { ... } }`
- **THEN** any dobby dispatcher skill SHALL read the file, accept `"github"` as the active backend, and proceed to route to the corresponding backend implementation

#### Scenario: Config file present but backend value unrecognized
- **WHEN** `.dobby/config.json` exists but `backend` is missing or holds a value other than `"ado"` or `"github"`
- **THEN** the dispatcher SHALL stop, report the unrecognized value to the user, and ask them to correct the file rather than guess

### Requirement: Interactive backend selection on first run
The system SHALL prompt the user for the project's backend when `.dobby/config.json` is missing and persist the answer for subsequent invocations. The dispatcher SHALL NOT collect backend connection details (organization, repo, etc.) at this stage — only the backend selector.

#### Scenario: Config file missing
- **WHEN** a dispatcher runs and `.dobby/config.json` does not exist
- **THEN** the dispatcher SHALL ask the user whether the project uses Azure DevOps or GitHub, write `{ "backend": "<choice>" }` to `.dobby/config.json` (creating the `.dobby/` directory if needed), and continue to route

#### Scenario: Backend chosen but connection details deferred
- **WHEN** the user selects a backend on first run via the dispatcher
- **THEN** the dispatcher SHALL write only the `backend` selector and SHALL NOT prompt for organization, project, team, owner, repo, or other connection fields — those are collected by the backend implementation skill on its own first run

### Requirement: Dispatcher hands off to backend implementation
The system SHALL provide three dispatcher skills (`dobby-create-pbi`, `dobby-close-pbi`, `dobby-propose-from-pbi`) whose sole responsibility is to resolve the active backend and follow the matching backend implementation skill. Dispatchers SHALL NOT perform any backend-specific work themselves.

#### Scenario: Dispatcher routes to ADO implementation
- **WHEN** the active backend is `"ado"` and the user invokes `dobby-close-pbi` (by name or intent)
- **THEN** the dispatcher SHALL Read `skills/dobby-ado-close-pbi/SKILL.md` and follow those instructions from the top, treating the user's original request as the input

#### Scenario: Dispatcher routes to GitHub implementation
- **WHEN** the active backend is `"github"` and the user invokes `dobby-close-pbi` (by name or intent)
- **THEN** the dispatcher SHALL Read `skills/dobby-gh-close-issue/SKILL.md` and follow those instructions from the top, treating the user's original request as the input

#### Scenario: Dispatcher never performs backend operations
- **WHEN** any dispatcher executes
- **THEN** the dispatcher SHALL NOT invoke `az`, `gh`, or any backend-specific helper script, and SHALL NOT modify tracker state directly

### Requirement: Skill description discipline prevents picker collision
The system SHALL set the description fields in skill frontmatter such that the dispatcher is the preferred match for casual intent ("close this", "close this pbi"). Backend implementation skills SHALL describe themselves as internal and invoked by the dispatcher to discourage direct selection.

#### Scenario: Dispatcher description signals "auto-routes"
- **WHEN** an LLM-based skill picker reads available skill descriptions
- **THEN** each dispatcher's description SHALL explicitly state that it auto-detects the backend from `.dobby/config.json` and SHALL list the natural-language phrases it handles

#### Scenario: Backend skill description signals "internal"
- **WHEN** an LLM-based skill picker reads a backend skill's description
- **THEN** the description SHALL begin with "Internal —" and SHALL note that the skill is invoked by the corresponding dispatcher rather than directly

### Requirement: One-time migration from legacy config file
The system SHALL provide a migration script that transforms an existing `.dobby/azdo-defaults.json` into `.dobby/config.json` without data loss. The migration SHALL be idempotent and SHALL NOT overwrite an existing `.dobby/config.json` unless the user explicitly forces it.

#### Scenario: Migration on a project with only the legacy file
- **WHEN** the migration script runs in a project where `.dobby/azdo-defaults.json` exists and `.dobby/config.json` does not
- **THEN** the script SHALL read the legacy file, write a new `.dobby/config.json` with shape `{ "backend": "ado", "ado": <legacy content> }`, and remove the legacy file only after the new file is successfully written

#### Scenario: Migration is a no-op when already migrated
- **WHEN** the migration script runs in a project where `.dobby/config.json` already exists
- **THEN** the script SHALL exit successfully without modifying any file and SHALL print a clear "already migrated" message

#### Scenario: Migration refuses to overwrite without force
- **WHEN** both `.dobby/azdo-defaults.json` and `.dobby/config.json` exist and the script is run without `--force`
- **THEN** the script SHALL exit with a non-zero status, refuse to overwrite, and instruct the user to inspect both files manually

#### Scenario: Migration triggered automatically by dispatcher
- **WHEN** any dispatcher detects `.dobby/azdo-defaults.json` and no `.dobby/config.json` on first invocation
- **THEN** the dispatcher SHALL run the migration script before proceeding to route
