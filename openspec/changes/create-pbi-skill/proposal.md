## Why

Dobby needs a way to create PBIs in Azure DevOps directly from a Copilot CLI session. Currently there's no automated path from a short description or email to a properly structured PBI with the correct project, feature/epic, area path, and iteration. A Copilot CLI skill would make this a single conversational command, removing the friction of navigating the Azure DevOps UI.

## What Changes

- Introduce a new Copilot CLI skill (`create-pbi`) that connects to Azure DevOps using the user's credentials
- The skill collects: title, description, project, feature/epic parent, area path, and iteration
- It leverages the Azure DevOps CLI (`az boards`) as a prerequisite for API interaction
- The skill is usable both as a reusable skill file and interactively in the current session

## Capabilities

### New Capabilities
- `pbi-creation`: Skill that creates a new PBI work item in Azure DevOps with proper hierarchy (parent epic/feature), area path, and iteration assignment via the `az boards` CLI.

### Modified Capabilities
<!-- No existing capabilities to modify — this is the first skill in the project. -->

## Impact

- **Dependencies**: Requires Azure CLI (`az`) with the `azure-devops` extension installed and authenticated (`az login`)
- **New files**: A Copilot CLI skill file at `.github/skills/create-pbi/` (or similar location)
- **Systems**: Interacts with Azure DevOps Work Items API via `az boards work-item create`
- **Users**: Users must have appropriate permissions on the target Azure DevOps project
