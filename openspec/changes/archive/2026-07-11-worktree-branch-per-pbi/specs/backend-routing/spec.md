## MODIFIED Requirements

### Requirement: Project tracker configuration file
The system SHALL read project-level tracker configuration from `.dobby/config.json` in the repository root. The file SHALL contain a top-level `backend` field whose value is `"ado"`, `"github"`, or `"combined"`, and per-backend sub-objects (`ado`, `github`) containing connection details for the selected backend. When `backend` is `"combined"`, both `ado` and `github` sub-objects SHALL be present.

#### Scenario: Config file present with valid backend
- **WHEN** `.dobby/config.json` exists and contains `{ "backend": "ado", "ado": { ... } }`
- **THEN** any dobby dispatcher skill SHALL read the file, accept `"ado"` as the active backend, and proceed to route to the corresponding backend implementation

#### Scenario: Config file present with valid github backend
- **WHEN** `.dobby/config.json` exists and contains `{ "backend": "github", "github": { ... } }`
- **THEN** any dobby dispatcher skill SHALL read the file, accept `"github"` as the active backend, and proceed to route to the corresponding backend implementation

#### Scenario: Config file present with valid combined backend
- **WHEN** `.dobby/config.json` exists and contains `{ "backend": "combined", "ado": { ... }, "github": { ... } }`
- **THEN** any dobby dispatcher skill SHALL read the file, accept `"combined"` as the active backend, and route work-item operations to ADO backend skills and repo/PR operations to GitHub backend skills

#### Scenario: Config file present but backend value unrecognized
- **WHEN** `.dobby/config.json` exists but `backend` is missing or holds a value other than `"ado"`, `"github"`, or `"combined"`
- **THEN** the dispatcher SHALL stop, report the unrecognized value to the user, and ask them to correct the file rather than guess

### Requirement: Dispatcher hands off to backend implementation
The system SHALL provide three dispatcher skills (`dobby-create-pbi`, `dobby-close-pbi`, `dobby-propose-from-pbi`) whose sole responsibility is to resolve the active backend and follow the matching backend implementation skill. For `"combined"` backend, dispatchers SHALL coordinate between ADO and GitHub backend skills based on operation type. Dispatchers SHALL NOT perform any backend-specific work themselves.

#### Scenario: Dispatcher routes to ADO implementation
- **WHEN** the active backend is `"ado"` and the user invokes `dobby-close-pbi` (by name or intent)
- **THEN** the dispatcher SHALL Read `skills/dobby-ado-close-pbi/SKILL.md` and follow those instructions from the top, treating the user's original request as the input

#### Scenario: Dispatcher routes to GitHub implementation
- **WHEN** the active backend is `"github"` and the user invokes `dobby-close-pbi` (by name or intent)
- **THEN** the dispatcher SHALL Read `skills/dobby-gh-close-issue/SKILL.md` and follow those instructions from the top, treating the user's original request as the input

#### Scenario: Dispatcher routes combined-mode close
- **WHEN** the active backend is `"combined"` and the user invokes `dobby-close-pbi`
- **THEN** the dispatcher SHALL route work-item state transitions and evidence uploads to `dobby-ado-close-pbi`, and PR-related operations (evidence commit to branch, PR update) to `dobby-gh-close-issue`

#### Scenario: Dispatcher never performs backend operations
- **WHEN** any dispatcher executes
- **THEN** the dispatcher SHALL NOT invoke `az`, `gh`, or any backend-specific helper script, and SHALL NOT modify tracker state directly
