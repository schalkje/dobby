Link the implementation commit, branch, and (when one exists) PR to the work item. The right link type depends on **whether the org's ADO can reach the repo** — read this from the `ado.devLinks` block of `.dobby/config.json`:

```json
"devLinks": {
  "repoReachableFromAdo": true,
  "host": "github",
  "githubConnectionId": "<guid-of-boards-github-connection>",
  "adoProjectId": "<guid>",
  "adoRepoId": "<guid>"
}
```

- `repoReachableFromAdo` (bool, **required**): `true` for ADO Repos in this org or company-GitHub repos that have a Boards <-> GitHub connection set up; `false` for private personal/external repos that the org's ADO cannot reach.
- `host` (`"github"` | `"ado"`): the implementation repo's host. Optional — usually inferred from the URL.
- `githubConnectionId`: the GUID of the project's Boards <-> GitHub connection. Required when `repoReachableFromAdo: true` and `host: "github"`.
- `adoProjectId` / `adoRepoId`: GUIDs for ADO Repos. Required when `host: "ado"`.

| Repo location | `repoReachableFromAdo` | Link type | Where it shows |
|---|---|---|---|
| ADO Repos in same org | `true` | ArtifactLink | Development section |
| Company GitHub with Boards <-> GitHub connection | `true` | ArtifactLink | Development section |
| Private personal GitHub, external repo, anything ADO can't reach | `false` | Hyperlink | Links panel |

**Why this matters**: the API will *accept* a `vstfs:///GitHub/Commit/...` ArtifactLink even when no connection exists, but the work item form will then display "GitHub Commit link could not be read" because ADO has no way to fetch the commit metadata. **Posting an unresolvable ArtifactLink is worse than posting a Hyperlink** — don't do it. If `repoReachableFromAdo` is missing or unsure, default to Hyperlink.

If `devLinks` is missing entirely, ask the user once and write it back into the `ado` block of `.dobby/config.json` so future work items use the right type without prompting.

**Discovery (when `repoReachableFromAdo: true`):**

- GitHub: `GET <org>/<project>/_apis/githubconnections?api-version=7.2-preview.1` — copy the `id` GUID into `devLinks.githubConnectionId`. Also check `GET <org>/_apis/serviceendpoint/endpoints?type=github` for an org-level connection.
- ADO Repos: `az repos show --repository <name> --org "<org-url>" --project "<project>" --query "{p:project.id, r:id}" -o json` — store both GUIDs in `devLinks`.

Run `azdo-add-dev-links.py` — it picks the right relation type based on the flags it receives:

```bash
python skills/_lib/azdo-add-dev-links.py \
    --work-item-id <work-item-id> \
    --org "<org-url>" \
    --project "<project-name>" \
    --commit-url "<commit-url>" --commit-comment "<subject> (<short-sha>)" \
    --branch-url "<branch-url>" --branch-comment "Implementation branch" \
    [--pr-url "<pr-url>" --pr-comment "PR #<num>"] \
    [--gh-connection-id <guid>] \
    [--ado-project-id <guid> --ado-repo-id <guid>]
```

Behaviour:
- **GitHub URLs**: ArtifactLink iff `--gh-connection-id` (or `GH_BOARDS_CONNECTION_ID` env var) is supplied; otherwise Hyperlink. (GitHub branches always use Hyperlink — there's no GitHub Branch artifact-link type.)
- **ADO Repos URLs**: ArtifactLink iff both `--ado-project-id` and `--ado-repo-id` (or `ADO_PROJECT_ID` / `ADO_REPO_ID`) are supplied; otherwise Hyperlink.
- **Anything else**: Hyperlink.

Artifact-link URI formats (the script encodes these for you):
- `vstfs:///GitHub/Commit/<connection-id>%2F<sha>` — name `"GitHub Commit"`
- `vstfs:///GitHub/PullRequest/<connection-id>%2F<num>` — name `"GitHub Pull Request"`
- `vstfs:///Git/Commit/<projectId>%2f<repoId>%2f<sha>` — name `"Fixed in Commit"`
- `vstfs:///Git/Ref/<projectId>%2f<repoId>%2fGBrefs%2fheads%2f<branch>` — name `"Branch"`
- `vstfs:///Git/PullRequestId/<projectId>%2f<repoId>%2f<num>` — name `"Pull Request"`

**Always**:
1. Push the branch to origin first (otherwise the URLs 404 in browsers).
2. Use the **full 40-char SHA** in commit URLs — short SHAs work in GitHub but not in all hosts.
3. Add the links **before** posting the closing comment so users see them right away; the same URLs should also appear in the `### Source` section of the closing comment for inline visibility.
