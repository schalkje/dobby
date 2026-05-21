## ADDED Requirements

### Requirement: Combined backend configuration
The system SHALL support `"combined"` as a valid value for the `backend` field in `.dobby/config.json`. When `backend` is `"combined"`, both the `ado` and `github` sub-objects SHALL be present and contain their respective connection details.

#### Scenario: Valid combined config
- **WHEN** `.dobby/config.json` contains `{ "backend": "combined", "ado": { "organization": "...", "project": "...", "team": "..." }, "github": { "owner": "...", "repo": "..." } }`
- **THEN** any dobby dispatcher skill SHALL accept the configuration and route operations according to combined-mode routing rules

#### Scenario: Combined config missing ADO block
- **WHEN** `.dobby/config.json` contains `{ "backend": "combined" }` without an `ado` sub-object
- **THEN** the dispatcher SHALL prompt the user to provide ADO connection details (organization, project, team) and persist them into the `ado` block

#### Scenario: Combined config missing GitHub block
- **WHEN** `.dobby/config.json` contains `{ "backend": "combined" }` without a `github` sub-object
- **THEN** the dispatcher SHALL prompt the user to provide GitHub connection details (owner, repo) and persist them into the `github` block

### Requirement: Combined-mode operation routing
The system SHALL route operations in combined mode based on operation type: work-item operations go to ADO backend skills, repository/PR operations go to GitHub backend skills.

#### Scenario: Work item creation in combined mode
- **WHEN** `backend` is `"combined"` and the user invokes `dobby-create-pbi`
- **THEN** the dispatcher SHALL route to `dobby-ado-create-pbi` for work item creation in Azure DevOps

#### Scenario: PBI closure in combined mode
- **WHEN** `backend` is `"combined"` and the user invokes `dobby-close-pbi`
- **THEN** the dispatcher SHALL route work-item state changes and evidence uploads to `dobby-ado-close-pbi`, and PR-related operations (evidence commit to branch, PR description update) to `dobby-gh-close-issue`

#### Scenario: Spec proposal in combined mode
- **WHEN** `backend` is `"combined"` and the user invokes `dobby-propose-from-pbi`
- **THEN** the dispatcher SHALL fetch the work item from ADO via `dobby-ado-propose-from-pbi` and create the OpenSpec change with traceability linking to the ADO PBI URL

#### Scenario: Dev links point to GitHub URLs
- **WHEN** a PBI is closed in combined mode and dev links are added to ADO
- **THEN** the system SHALL use GitHub URLs for commit, branch, and PR links (as the repo is hosted on GitHub), using `azdo-add-dev-links.py` with GitHub URL format

### Requirement: Interactive combined backend selection
The system SHALL offer `"combined"` as a third option (alongside `"ado"` and `"github"`) when prompting the user on first run.

#### Scenario: First run backend selection includes combined option
- **WHEN** a dispatcher runs and `.dobby/config.json` does not exist
- **THEN** the dispatcher SHALL ask the user to choose between "Azure DevOps", "GitHub", or "Combined (ADO work items + GitHub repo)" and persist the selection

### Requirement: Identity verification for both backends
The system SHALL verify authentication for both ADO (`az account show`) and GitHub (`gh auth status`) at the start of any combined-mode operation to catch wrong-account issues early.

#### Scenario: Both identities displayed in combined mode
- **WHEN** any backend skill runs in combined mode
- **THEN** the system SHALL display both the ADO identity (from `az account show`) and GitHub identity (from `gh auth status`) before performing any operations
