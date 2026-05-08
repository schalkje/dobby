# dobby
Agentic DevOps

## Skills

### dobby-create-pbi

Creates a Product Backlog Item in Azure DevOps from a conversational request. Collects fields interactively (title, description, project, area path, iteration, parent), validates prerequisites, and creates the work item via the `az boards` CLI.

**Prerequisites**: Azure CLI with the `azure-devops` extension installed and authenticated (`az login`).

**Usage examples**:
- `Create a PBI titled "Add login page" in project MyProject under feature 1234`
- `Create a PBI "Fix header alignment"`
- `Create a PBI from this: "We need dark mode in settings"`

See [`.github/skills/dobby-create-pbi/SKILL.md`](.github/skills/dobby-create-pbi/SKILL.md) for full details.
