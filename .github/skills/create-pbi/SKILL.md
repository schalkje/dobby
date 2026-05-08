---
name: create-pbi
description: Create a Product Backlog Item in Azure DevOps. Collects fields interactively, validates prerequisites, and creates the work item via the az boards CLI.
metadata:
  author: dobby
  version: "1.0"
---

Create a Product Backlog Item (PBI) in Azure DevOps from a conversational request.

**Input**: The user may provide any combination of: title, description, project, area path, iteration, parent work item (ID or keywords). Any missing required fields are collected interactively.

## Steps

### 1. Validate Prerequisites

Before doing anything else, verify that the required tooling is available.

**1a. Check Azure CLI**
```bash
az version --output json
```
- If the `az` command is not found, stop and tell the user:
  > Azure CLI is not installed. Install it from https://learn.microsoft.com/cli/azure/install-azure-cli then run this skill again.

**1b. Check azure-devops extension**
```bash
az extension list --output json
```
- Parse the JSON output and look for an entry with `"name": "azure-devops"`.
- If not found, stop and tell the user:
  > The Azure DevOps CLI extension is not installed. Run: `az extension add --name azure-devops`

**1c. Check authentication**
```bash
az account show --output json
```
- If this fails with an auth error, stop and tell the user:
  > You are not logged in to Azure CLI. Run: `az login`

### 2. Resolve Organization and Project

**2a. Check for configured defaults**
```bash
az devops configure --list
```
- Look for `organization` and `project` defaults in the output.
- Store any found defaults for later use.

**2b. Determine organization**
- If the user provided an organization, use it.
- If a default organization is configured, use it and inform the user.
- If neither: ask the user for their Azure DevOps organization URL (e.g., `https://dev.azure.com/myorg`).

**2c. Validate Azure DevOps access**
```bash
az devops project list --organization "<org-url>" --output json
```
- If this fails with an authentication or permission error, tell the user:
  > Cannot access Azure DevOps organization. Ensure you have access and try `az login` if needed.
- Parse the list of projects for use in the next step.

**2d. Determine project**
- If the user provided a project, use it (validate it exists in the project list).
- If a default project is configured and exists, use it and inform the user.
- If neither: present the list of available projects and ask the user to select one.
- If the user provided a project name that does not match any available project, show the available projects and ask the user to choose.

### 3. Collect PBI Fields

For each field below, skip the prompt if the user already provided a value.

**3a. Title** (required)
- If the user has not provided a title, ask for one. Do not proceed without a title.

**3b. Description** (optional)
- If not provided, ask the user if they want to add a description. Accept free-form text or skip.

**3c. Area path**
- List available area paths:
  ```bash
  az boards area team list --team "<project-name> Team" --project "<project-name>" --organization "<org-url>" --output json
  ```
  - If the team-scoped command fails, inform the user and allow manual entry of an area path.
- If the user did not specify an area path, present the available paths and ask the user to select one, or accept the project root as the default.
- Allow the user to type a path manually if their desired path is not listed.

**3d. Iteration**
- List available iterations:
  ```bash
  az boards iteration team list --team "<project-name> Team" --project "<project-name>" --organization "<org-url>" --output json
  ```
  - If the team-scoped command fails, inform the user and allow manual entry of an iteration path.
- If the user did not specify an iteration:
  - Look for an iteration whose date range includes today (current iteration).
  - If a current iteration is found, suggest it as the default.
  - If not, present the list and ask the user to select one.
- Allow the user to type a path manually if their desired iteration is not listed.

**3e. Parent work item** (optional)
- If the user provided a parent work item ID (numeric), use it directly.
- If the user provided keywords or a title for the parent:
  ```bash
  az boards query --wiql "SELECT [System.Id], [System.Title], [System.WorkItemType] FROM WorkItems WHERE ([System.WorkItemType] = 'Feature' OR [System.WorkItemType] = 'Epic') AND [System.Title] CONTAINS '<keywords>'" --project "<project-name>" --organization "<org-url>" --output json
  ```
  - Present matching results and ask the user to confirm which parent to use.
- If the user did not mention a parent: ask whether to create the PBI without a parent or to search for one.

### 4. Confirm Before Creation

Before creating the work item, display a summary of all collected fields:

```
## PBI Summary

- **Title**: <title>
- **Description**: <description or "none">
- **Project**: <project>
- **Area Path**: <area-path>
- **Iteration**: <iteration>
- **Parent**: <parent-id and title, or "none">
```

Ask the user to confirm or edit any field before proceeding.

### 5. Create the PBI

**5a. Create the work item**
```bash
az boards work-item create --title "<title>" --type "Product Backlog Item" --project "<project-name>" --area "<area-path>" --iteration "<iteration-path>" --description "<description>" --organization "<org-url>" --output json
```
- If creation fails, display the error message from `az`. Common causes:
  - Permission denied → "You may not have permission to create work items in this project."
  - Invalid area/iteration path → "The specified area path or iteration does not exist. Please check and try again."
  - Work item type not found → "The work item type 'Product Backlog Item' is not available in this project. This project may use a different process template (e.g., 'User Story' for Agile or 'Requirement' for CMMI)."
- Do **not** retry creation automatically to avoid duplicates.

**5b. Parse the result**
- Extract from the JSON output: `id`, `fields["System.Title"]`, and construct the URL as `<org-url>/<project>/_workitems/edit/<id>`.

**5c. Link parent (if specified)**
- If a parent work item was selected, add the relation:
  ```bash
  az boards work-item relation add --id <new-pbi-id> --relation-type "parent" --target-id <parent-id> --organization "<org-url>" --output json
  ```
- If linking fails:
  - **Do not** delete or re-create the PBI.
  - Display a partial-success message:
    > ⚠ PBI created successfully (ID: <id>) but parent linking failed: <error>. You can link it manually or run: `az boards work-item relation add --id <id> --relation-type "parent" --target-id <parent-id>`

### 6. Display Result

On full success, display:

```
## ✓ PBI Created

- **ID**: <work-item-id>
- **Title**: <title>
- **Project**: <project>
- **Area Path**: <area-path>
- **Iteration**: <iteration>
- **Parent**: <parent-id> (if linked)
- **URL**: <direct-url>
```

## Error Handling

- **Auth expiry mid-flow**: If any `az` command fails with an authentication error after initial validation passed, inform the user:
  > Your authentication may have expired. Please run `az login` and try again.
- **Network errors**: If commands fail with connection errors, suggest checking network connectivity.
- **Never retry PBI creation automatically** — always ask the user before retrying to prevent duplicate work items.
- **Partial success**: If the PBI is created but a subsequent step (parent linking) fails, clearly report what succeeded and what failed, including the created work item ID so the user can find it.

## Guardrails

- Always validate prerequisites before attempting any Azure DevOps operations
- Always confirm the full PBI summary with the user before creation
- Skip prompts for fields the user already provided in their request
- Never retry creation without explicit user confirmation
- If a field value is invalid (area path, iteration), re-prompt rather than failing
- Use `--output json` on all `az` commands and parse JSON for reliability
- Include `--organization` on all `az devops`/`az boards` commands unless a default is confirmed

## Usage Examples

**Full specification:**
> Create a PBI titled "Add login page" in project MyProject under feature 1234, area path "MyProject\Web", iteration "Sprint 5"

**Minimal:**
> Create a PBI "Fix header alignment"

**From an email or description:**
> Create a PBI from this: "We need to add a dark mode toggle to the settings page. Users have been requesting this for a while."
