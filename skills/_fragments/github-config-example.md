Read the `github` block from `.dobby/config.json` in the repository root. Example shape:

```json
{
  "backend": "github",
  "github": {
    "owner": "myorg",
    "repo": "myrepo",
    "defaultLabels": ["needs-triage"]
  }
}
```

`owner` and `repo` are required. `defaultLabels` are applied automatically when the user does not specify labels. If `owner` or `repo` is missing, collect it during the first run and offer to persist it back to `.dobby/config.json` at the end (preserve `backend` and any other top-level keys).
