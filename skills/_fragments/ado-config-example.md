Read the `ado` block from `.dobby/config.json` in the repository root. Example shape:

```json
{
  "backend": "ado",
  "ado": {
    "organization": "https://dev.azure.com/myorg/",
    "project": "MyProject",
    "team": "MyTeam"
  }
}
```

The values under `ado` eliminate repeated prompts for organization, project, and team. If the `ado` block is missing or incomplete, collect the missing fields interactively during the run and offer to persist them back to `.dobby/config.json` at the end (preserve `backend` and any other top-level keys; create the `.dobby/` directory and the file if needed). Flows that add development links also read an optional `ado.devLinks` block — its fields are documented in the dev-links step of the close and implement flows.
