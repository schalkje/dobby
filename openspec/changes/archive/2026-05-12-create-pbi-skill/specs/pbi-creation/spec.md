## ADDED Requirements

### Requirement: Skill creates a PBI in Azure DevOps
The skill SHALL create a Product Backlog Item work item in the specified Azure DevOps project using the `az boards work-item create` CLI command.

#### Scenario: Successful PBI creation with all fields provided
- **WHEN** the user provides a title, description, project, area path, iteration, and parent work item ID
- **THEN** the skill creates a PBI with all specified fields and returns the work item ID and URL

#### Scenario: Successful PBI creation with minimal fields
- **WHEN** the user provides only a title and project
- **THEN** the skill creates a PBI with the title in the specified project using default area path and current iteration

### Requirement: Skill validates prerequisites
The skill SHALL check that the Azure CLI and azure-devops extension are installed and that the user is authenticated before attempting to create a work item.

#### Scenario: Azure CLI not installed
- **WHEN** the `az` command is not available on the system PATH
- **THEN** the skill reports the issue and provides installation instructions without attempting the create operation

#### Scenario: Azure DevOps extension not installed
- **WHEN** `az` is available but the `azure-devops` extension is not installed
- **THEN** the skill reports the issue and provides the command `az extension add --name azure-devops`

#### Scenario: User not authenticated
- **WHEN** `az` returns an authentication error
- **THEN** the skill prompts the user to run `az login` and does not create the work item

### Requirement: Skill interactively collects missing fields
The skill SHALL prompt the user for any required fields that were not provided in the initial request, offering available options where possible.

#### Scenario: Project not specified
- **WHEN** the user does not specify a project
- **THEN** the skill lists available projects via `az devops project list` and asks the user to select one

#### Scenario: Area path not specified
- **WHEN** the user does not specify an area path
- **THEN** the skill lists available area paths for the selected project and asks the user to choose or accept the default

#### Scenario: Iteration not specified
- **WHEN** the user does not specify an iteration
- **THEN** the skill lists available iterations for the selected project/team and asks the user to choose or uses the current iteration

### Requirement: Skill supports parent linking
The skill SHALL allow the user to specify a parent work item (epic or feature) to link the new PBI under.

#### Scenario: Parent specified by ID
- **WHEN** the user provides a parent work item ID
- **THEN** the skill creates the PBI with a parent relation to the specified work item

#### Scenario: Parent specified by title search
- **WHEN** the user provides a parent work item title or keywords instead of an ID
- **THEN** the skill queries matching features/epics and asks the user to confirm the correct parent before creating the PBI

#### Scenario: No parent specified
- **WHEN** the user does not specify a parent
- **THEN** the skill asks whether to create the PBI without a parent or to search for one

### Requirement: Skill reports creation result
The skill SHALL display the created PBI's ID, title, and a direct URL to the work item in Azure DevOps after successful creation.

#### Scenario: Successful creation output
- **WHEN** a PBI is successfully created
- **THEN** the skill outputs the work item ID, title, assigned area path, iteration, and a clickable URL
