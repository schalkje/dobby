#!/usr/bin/env python3
"""
Azure DevOps Work Item — Development Link Adder

Adds links from a work item to the implementation commit / branch / pull request.
Chooses the right relation type based on the URL host and whether a Boards <-> Git
connection is available:

    GitHub (github.com)
        Default: Hyperlink (universal — appears in the Links panel)
        With --gh-connection-id <guid>: ArtifactLink (Development section)
            commit  -> vstfs:///GitHub/Commit/<conn-id>%2F<sha>
            pull    -> vstfs:///GitHub/PullRequest/<conn-id>%2F<num>
        (Branches don't have a GitHub artifact link type — always Hyperlink.)
        WARNING: Without a real, working Boards <-> GitHub connection, the API
        will accept some `vstfs:///GitHub/...` URIs but the work item form will
        display "GitHub Commit link could not be read". Stick to Hyperlinks
        unless you have verified the connection works.

    Azure DevOps Repos (dev.azure.com/.../_git/...)
        ArtifactLink (Development section). Requires --ado-project-id and
        --ado-repo-id (both GUIDs); also accepted via ADO_PROJECT_ID and
        ADO_REPO_ID env vars.
            commit  -> vstfs:///Git/Commit/<pid>%2f<rid>%2f<sha>
            branch  -> vstfs:///Git/Ref/<pid>%2f<rid>%2fGBrefs%2fheads%2f<branch>
            pull    -> vstfs:///Git/PullRequestId/<pid>%2f<rid>%2f<num>

    Anything else
        Hyperlink fallback.

Usage:
    python azdo-add-dev-links.py \\
        --work-item-id 12345 \\
        --org "https://dev.azure.com/myorg" \\
        --project "MyProject" \\
        --commit-url https://github.com/owner/repo/commit/<full-sha> \\
        --commit-comment "feat: ... (sha)" \\
        --branch-url https://github.com/owner/repo/tree/<branch> \\
        --branch-comment "Implementation branch" \\
        [--pr-url https://github.com/.../pull/123 --pr-comment "PR #123"] \\
        [--gh-connection-id <guid>]

Notes:
    * Push the branch to origin BEFORE running this. Unpushed URLs 404.
    * Use the FULL 40-character SHA in --commit-url. Short SHAs aren't
      universally resolvable.
    * If a relation already exists, the script reports it but does not fail.
"""
import argparse, base64, json, os, re, ssl, subprocess, sys, urllib.error, urllib.parse, urllib.request

API_VERSION = "7.2-preview.3"
ADO_RESOURCE_ID = "499b84ac-1321-427f-aa17-267ca6975798"

GH_COMMIT_RE = re.compile(r"^https?://github\.com/([^/]+)/([^/]+)/commit/([0-9a-f]{7,40})/?$", re.I)
GH_TREE_RE   = re.compile(r"^https?://github\.com/([^/]+)/([^/]+)/tree/(.+?)/?$", re.I)
GH_PR_RE     = re.compile(r"^https?://github\.com/([^/]+)/([^/]+)/pull/(\d+)/?$", re.I)
ADO_COMMIT_RE = re.compile(r"^https?://dev\.azure\.com/[^/]+/[^/]+/_git/[^/]+/commit/([0-9a-f]{7,40})", re.I)
ADO_BRANCH_RE = re.compile(r"^https?://dev\.azure\.com/[^/]+/[^/]+/_git/[^/]+\?version=GB(.+?)(?:&|$)", re.I)
ADO_PR_RE     = re.compile(r"^https?://dev\.azure\.com/[^/]+/[^/]+/_git/[^/]+/pullrequest/(\d+)", re.I)


def get_token():
    pat = os.environ.get("AZURE_DEVOPS_EXT_PAT")
    if pat:
        return "Basic", base64.b64encode(f":{pat}".encode()).decode()
    tok = os.environ.get("ADO_TOKEN")
    if tok:
        return "Bearer", tok
    shell = sys.platform == "win32"
    tok = subprocess.check_output(
        ["az", "account", "get-access-token", "--resource", ADO_RESOURCE_ID,
         "--query", "accessToken", "-o", "tsv"],
        text=True, stderr=subprocess.PIPE, shell=shell,
    ).strip()
    return "Bearer", tok


def hyperlink(url, comment):
    return {"rel": "Hyperlink", "url": url, "attributes": {"comment": comment}}


def build_relation(kind, url, comment, ado_project_id=None, ado_repo_id=None, gh_connection_id=None):
    """Return the relation dict to PATCH. kind in {'commit','branch','pr'}."""
    # GitHub — only use ArtifactLink if a connection ID was supplied
    if "github.com" in url:
        if gh_connection_id:
            if kind == "commit" and (m := GH_COMMIT_RE.match(url)):
                sha = m.group(3).lower()
                if len(sha) < 40:
                    print(f"WARN: short SHA in {url}; the link may not resolve.", file=sys.stderr)
                artifact = f"vstfs:///GitHub/Commit/{gh_connection_id}%2F{sha}"
                return {"rel": "ArtifactLink", "url": artifact,
                        "attributes": {"name": "GitHub Commit", "comment": comment}}
            if kind == "pr" and (m := GH_PR_RE.match(url)):
                num = m.group(3)
                artifact = f"vstfs:///GitHub/PullRequest/{gh_connection_id}%2F{num}"
                return {"rel": "ArtifactLink", "url": artifact,
                        "attributes": {"name": "GitHub Pull Request", "comment": comment}}
            # GitHub branches don't have an artifact link type
        return hyperlink(url, comment)

    # ADO Repos — use ArtifactLink when project/repo IDs are available
    if "dev.azure.com" in url and ado_project_id and ado_repo_id:
        pid, rid = ado_project_id, ado_repo_id
        if kind == "commit" and (m := ADO_COMMIT_RE.match(url)):
            sha = m.group(1).lower()
            artifact = f"vstfs:///Git/Commit/{pid}%2f{rid}%2f{sha}"
            return {"rel": "ArtifactLink", "url": artifact,
                    "attributes": {"name": "Fixed in Commit", "comment": comment}}
        if kind == "branch" and (m := ADO_BRANCH_RE.match(url)):
            branch = urllib.parse.unquote(m.group(1))
            artifact = f"vstfs:///Git/Ref/{pid}%2f{rid}%2fGBrefs%2fheads%2f{urllib.parse.quote(branch, safe='')}"
            return {"rel": "ArtifactLink", "url": artifact,
                    "attributes": {"name": "Branch", "comment": comment}}
        if kind == "pr" and (m := ADO_PR_RE.match(url)):
            num = m.group(1)
            artifact = f"vstfs:///Git/PullRequestId/{pid}%2f{rid}%2f{num}"
            return {"rel": "ArtifactLink", "url": artifact,
                    "attributes": {"name": "Pull Request", "comment": comment}}

    # Default: plain Hyperlink (Links panel)
    return hyperlink(url, comment)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--work-item-id", required=True, type=int)
    p.add_argument("--org", required=True, help="https://dev.azure.com/<org>")
    p.add_argument("--project", required=True)
    p.add_argument("--commit-url")
    p.add_argument("--commit-comment", default="Implementation commit")
    p.add_argument("--branch-url")
    p.add_argument("--branch-comment", default="Implementation branch")
    p.add_argument("--pr-url")
    p.add_argument("--pr-comment", default="Pull request")
    p.add_argument("--ado-project-id", default=os.environ.get("ADO_PROJECT_ID"),
                   help="GUID of the ADO project (only needed for ADO Repos URLs)")
    p.add_argument("--ado-repo-id", default=os.environ.get("ADO_REPO_ID"),
                   help="GUID of the ADO Repo (only needed for ADO Repos URLs)")
    p.add_argument("--gh-connection-id", default=os.environ.get("GH_BOARDS_CONNECTION_ID"),
                   help="GUID of the Boards-GitHub connection (only needed to render GitHub links in the Development section)")
    a = p.parse_args()

    inputs = []
    if a.commit_url: inputs.append(("commit", a.commit_url, a.commit_comment))
    if a.branch_url: inputs.append(("branch", a.branch_url, a.branch_comment))
    if a.pr_url:     inputs.append(("pr",     a.pr_url,     a.pr_comment))
    if not inputs:
        print("ERROR: at least one of --commit-url / --branch-url / --pr-url is required.", file=sys.stderr)
        sys.exit(2)

    patch = [{"op": "add", "path": "/relations/-",
              "value": build_relation(k, u, c, a.ado_project_id, a.ado_repo_id, a.gh_connection_id)}
             for (k, u, c) in inputs]

    scheme, val = get_token()
    url = f"{a.org.rstrip('/')}/{a.project}/_apis/wit/workItems/{a.work_item_id}?api-version={API_VERSION}"
    req = urllib.request.Request(url, data=json.dumps(patch).encode("utf-8"), method="PATCH")
    req.add_header("Content-Type", "application/json-patch+json")
    req.add_header("Authorization", f"{scheme} {val}")
    try:
        r = json.loads(urllib.request.urlopen(req, context=ssl.create_default_context()).read())
        print(json.dumps({
            "workItemId": a.work_item_id,
            "rev": r.get("rev"),
            "added": [{"rel": op["value"]["rel"],
                       "name": op["value"]["attributes"].get("name", ""),
                       "url": op["value"]["url"],
                       "comment": op["value"]["attributes"].get("comment")} for op in patch],
        }, indent=2))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        if "RelationAlreadyExistsException" in body:
            print(f"WARN HTTP {e.code}: relation already exists — nothing to do.", file=sys.stderr)
            sys.exit(0)
        print(f"ERROR HTTP {e.code}: {body[:500]}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
