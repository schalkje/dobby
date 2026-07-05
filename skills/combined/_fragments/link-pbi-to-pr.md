## Phase 9d: Link the PBI to the PR (Azure DevOps)

**Combined mode only.** The work item is an Azure DevOps PBI but the repo and PR are on GitHub, so after the PR exists, connect to ADO and attach the GitHub commit / branch / PR as development links on the PBI — this is what gives the ADO board traceability back to the implementation.

Read the `ado` block from `.dobby/config.json` (`organization`, `project`, and `devLinks`). The link type depends on `ado.devLinks.repoReachableFromAdo`: with a configured `githubConnectionId` (and `repoReachableFromAdo: true`) the commit/PR attach as ArtifactLinks; otherwise as plain Hyperlinks (always resolvable).

```bash
python skills/_lib/azdo-add-dev-links.py \
    --work-item-id <pbi-id> --org "<org-url>" --project "<project>" \
    --commit-url "https://github.com/<owner>/<repo>/commit/<full-sha>" --commit-comment "<subject> (<short-sha>)" \
    --branch-url "https://github.com/<owner>/<repo>/tree/<branch>" --branch-comment "Implementation branch" \
    --pr-url "<pr-url>" --pr-comment "PR #<pr-number>" \
    [--gh-connection-id <guid>]
```

Push the branch first so the URLs resolve, and use the **full 40-char SHA**. The PBI id comes from the issue/branch context (`AB#<id>`, `pbi-<id>-*`, or the user). This step is in addition to the GitHub PR's own `Closes`/reference behavior; the ADO PBI is closed separately by `dobby-close-pbi`.
