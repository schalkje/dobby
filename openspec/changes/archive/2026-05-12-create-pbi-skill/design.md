## Context

Dobby is a greenfield agentic DevOps assistant. The first concrete capability is creating PBIs in Azure DevOps from a Copilot CLI session. There is no existing infrastructure — this skill will be the project's first functional component.

The Azure DevOps CLI (`az boards`) is a mature, well-supported tool that handles authentication, API versioning, and all work-item operations. It is available as an extension to the Azure CLI.

## Goals / Non-Goals

**Goals:**
- Provide a Copilot CLI skill that creates a PBI with a single conversational command
- Support setting: title, description, parent (epic/feature), area path, iteration
- Leverage `az boards` CLI — no direct REST calls needed
- Make the skill self-contained and reusable across sessions
- Interactively gather missing fields from the user when not provided

**Non-Goals:**
- No PBI editing, querying, or deletion (future skills)
- No custom field mappings beyond standard PBI fields
- No web UI or standalone application
- No management of Azure DevOps credentials (user must have `az login` done)
- No refinement, task breakdown, or implementation workflows (those are separate Dobby stages)

## Decisions

### 1. Use `az boards` CLI over REST API

**Decision**: Shell out to `az boards work-item create` rather than calling the Azure DevOps REST API directly.

**Rationale**: The CLI handles authentication (PAT, AAD), API versioning, and error formatting. It's already installed in most developer environments. This avoids implementing an HTTP client and auth flow.

**Alternative considered**: Direct REST via `curl` — rejected because it requires manual PAT management and URL construction.

### 2. Copilot CLI skill format (`.github/skills/create-pbi/`)

**Decision**: Implement as a Copilot CLI skill with a markdown instruction file and optional supporting scripts.

**Rationale**: Skills are the native extensibility mechanism for Copilot CLI. They get automatically discovered and can be invoked with `/skill-name` or by the agent.

### 3. Interactive field collection

**Decision**: The skill asks the user for any required fields not provided upfront (project, area path, iteration, parent).

**Rationale**: Users may not remember exact area paths or iteration names. The skill can list available options via `az boards iteration team list` and `az boards area team list` to help the user choose.

### 4. Prerequisite validation

**Decision**: The skill checks for `az` CLI and `azure-devops` extension at invocation time and provides clear setup instructions if missing.

**Rationale**: Failing fast with actionable guidance is better than a cryptic error mid-flow.

## Risks / Trade-offs

- **[CLI not installed]** → Skill checks prerequisites upfront and provides install commands (`az extension add --name azure-devops`)
- **[Auth expired]** → Skill detects auth errors from `az` output and prompts user to re-authenticate
- **[Wrong project/area path]** → Skill validates inputs by querying available values before creating the work item
- **[Rate limits]** → Unlikely for single PBI creation; not mitigated
- **[Skill format changes]** → Copilot CLI skill format is still evolving; keep the skill minimal to reduce maintenance surface
