## Phase 9d: Link the PBI to the PR (Azure DevOps)

**Combined mode only.** The work item is an Azure DevOps PBI but the repo and PR are on GitHub, so after the PR exists, connect to ADO and attach the GitHub commit / branch / PR as development links on the PBI — this is what gives the ADO board traceability back to the implementation. The PBI id comes from the issue/branch context (`AB#<id>`, `pbi-<id>-*`, or the user). This step is in addition to the GitHub PR's own `Closes`/reference behavior; the ADO PBI is closed separately by `dobby-close-pbi`.

Read the `ado` block from `.dobby/config.json` (`organization`, `project`, and `devLinks`). The commit URL is `https://github.com/<owner>/<repo>/commit/<full-sha>` and the branch URL is `https://github.com/<owner>/<repo>/tree/<branch>`. Then:

<!-- dobby:include:ado-dev-links -->
