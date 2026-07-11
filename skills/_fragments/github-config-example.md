Read the `github` block from `.dobby/config.json` in the repository root. Example shape:

```json
{
  "backend": "github",
  "github": {
    "owner": "myorg",
    "repo": "myrepo",
    "defaultLabels": ["needs-triage"],
    "projectNumber": 7
  }
}
```

`owner` and `repo` are required. `defaultLabels` are applied automatically when the user does not specify labels. `projectNumber` is optional and used only if the user asks to add the issue to a Projects v2 board. If `owner` or `repo` is missing, collect it during the first run and offer to persist it back to `.dobby/config.json` at the end (preserve `backend` and any other top-level keys).
