## Why

Dobby needs a way to create PBIs in Azure DevOps directly from a Copilot CLI session. Currently there's no automated path from a short description or email to a properly structured PBI with the correct project, feature/epic, area path, and iteration. A Copilot CLI skill would make this a single conversational command, removing the friction of navigating the Azure DevOps UI.

A two-phase approach (draft locally → push to ADO) adds value: users can review and edit the PBI before committing it, work offline, maintain a local audit trail, and benefit from a clearer separation of concerns.

## What Changes

- Introduce a new Copilot CLI skill (`create-pbi`) with a two-phase workflow:
  1. **Draft phase**: Gather all PBI information interactively and write it to a local markdown file for review
  2. **Push phase**: Read the local markdown and create the work item in Azure DevOps
- The skill collects: title, description, project, feature/epic parent, area path, and iteration
- Local drafts are stored as markdown files (e.g., `.dobby/pbi-drafts/<title-slug>.md`)
- It leverages the Azure DevOps CLI (`az boards`) as a prerequisite for the push phase
- The skill is usable both as a reusable skill file and interactively in the current session

## Capabilities

### New Capabilities
- `pbi-drafting`: Skill that interactively gathers PBI fields and writes a structured local markdown draft for review and editing before submission.
- `pbi-push`: Skill that reads a local PBI markdown draft and creates the work item in Azure DevOps with proper hierarchy (parent epic/feature), area path, and iteration assignment via the `az boards` CLI.

### Modified Capabilities
<!-- No existing capabilities to modify — this is the first skill in the project. -->

## Impact

- **Dependencies**: Requires Azure CLI (`az`) with the `azure-devops` extension installed and authenticated (`az login`) — only for the push phase
- **New files**: Copilot CLI skill files at `.github/skills/create-pbi/`; local draft storage at `.dobby/pbi-drafts/`
- **Systems**: Interacts with Azure DevOps Work Items API via `az boards work-item create` (push phase only)
- **Users**: Users must have appropriate permissions on the target Azure DevOps project
- **Local artifacts**: Markdown drafts persist locally, enabling offline workflow and audit trail
