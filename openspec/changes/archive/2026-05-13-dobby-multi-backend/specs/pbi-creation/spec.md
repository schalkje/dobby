## MODIFIED Requirements

### Requirement: Skill creates a PBI in Azure DevOps
The `dobby-ado-create-pbi` skill SHALL create a Product Backlog Item work item in the specified Azure DevOps project using the `az boards work-item create` CLI command. This skill SHALL be invoked only by the `dobby-create-pbi` dispatcher when the project's active backend (per `.dobby/config.json`) is `"ado"`. Direct invocation is permitted as an escape hatch but is not the primary entry point.

#### Scenario: Successful PBI creation with all fields provided
- **WHEN** the user provides a title, description, project, area path, iteration, and parent work item ID
- **THEN** the skill creates a PBI with all specified fields and returns the work item ID and URL

#### Scenario: Successful PBI creation with minimal fields
- **WHEN** the user provides only a title and project
- **THEN** the skill creates a PBI with the title in the specified project using default area path and current iteration

#### Scenario: Dispatcher routes to this skill when backend is ADO
- **WHEN** the user invokes `dobby-create-pbi` and `.dobby/config.json` has `backend: "ado"`
- **THEN** the dispatcher SHALL Read `skills/dobby-ado-create-pbi/SKILL.md` and follow its instructions from the top with the user's request as input

## ADDED Requirements

### Requirement: ADO connection details read from config
The `dobby-ado-create-pbi` skill SHALL read `organization`, `project`, and `team` from the `ado` block of `.dobby/config.json` rather than from a separate `.dobby/azdo-defaults.json` file. The legacy file SHALL no longer be consulted after migration.

#### Scenario: Config block present
- **WHEN** `.dobby/config.json` has a fully populated `ado` block
- **THEN** the skill SHALL use those values without prompting and SHALL NOT read `.dobby/azdo-defaults.json`

#### Scenario: Config block missing fields
- **WHEN** the `ado` block is partially populated or absent
- **THEN** the skill SHALL prompt the user for the missing fields, attempt the create operation, and persist the values into the `ado` block after the first successful create
