#!/usr/bin/env python3
"""
Azure DevOps Work Item — Comment Fetcher

Fetches comments (discussion thread) from a work item via the REST API.
Returns JSON with comment text, author, and date — suitable for agent
consumption during PBI refinement.

Usage:
    python azdo-get-comments.py \\
        --work-item-id 12345 \\
        --org "https://dev.azure.com/myorg" \\
        --project "MyProject"

    # Limit to most recent N comments (default: 50)
    python azdo-get-comments.py \\
        --work-item-id 12345 \\
        --org "https://dev.azure.com/myorg" \\
        --project "MyProject" \\
        --max-comments 20

Authentication (tried in order):
    1. AZURE_DEVOPS_EXT_PAT environment variable (PAT)
    2. ADO_TOKEN environment variable (Bearer token)
    3. `az account get-access-token` (AAD — requires Azure CLI)
"""

import argparse
import base64
import json
import os
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API_VERSION = "7.2-preview.4"
ADO_RESOURCE_ID = "499b84ac-1321-427f-aa17-267ca6975798"
MAX_RETRIES = 3
INITIAL_BACKOFF = 2
DEFAULT_MAX_COMMENTS = 50


def get_token():
    """Get an authentication token, trying multiple methods."""
    pat = os.environ.get("AZURE_DEVOPS_EXT_PAT")
    if pat:
        encoded = base64.b64encode(f":{pat}".encode()).decode()
        return "Basic", encoded

    token = os.environ.get("ADO_TOKEN")
    if token:
        return "Bearer", token

    try:
        shell = sys.platform == "win32"
        token = subprocess.check_output(
            ["az", "account", "get-access-token",
             "--resource", ADO_RESOURCE_ID,
             "--query", "accessToken", "-o", "tsv"],
            text=True, stderr=subprocess.PIPE, shell=shell
        ).strip()
        if token:
            return "Bearer", token
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    print("ERROR: No authentication method available.", file=sys.stderr)
    print("  Set AZURE_DEVOPS_EXT_PAT (PAT), ADO_TOKEN (Bearer), or run `az login`.", file=sys.stderr)
    sys.exit(1)


def fetch_comments(org_url, project, work_item_id, max_comments, auth_scheme, auth_value):
    """Fetch comments from a work item, newest first, up to max_comments."""
    org = org_url.rstrip("/")
    proj = urllib.parse.quote(project, safe="")
    ctx = ssl.create_default_context()

    all_comments = []
    continuation_token = None
    page_size = min(max_comments, 200)
    total_count = 0

    while len(all_comments) < max_comments:
        url = (
            f"{org}/{proj}/_apis/wit/workItems/{work_item_id}/comments"
            f"?api-version={API_VERSION}&$top={page_size}&order=desc"
        )
        if continuation_token:
            url += f"&continuationToken={continuation_token}"

        for attempt in range(MAX_RETRIES + 1):
            req = urllib.request.Request(url)
            req.add_header("Authorization", f"{auth_scheme} {auth_value}")

            try:
                resp = urllib.request.urlopen(req, context=ctx)
                data = json.loads(resp.read())
                break
            except urllib.error.HTTPError as e:
                if e.code in (429, 502, 503, 504) and attempt < MAX_RETRIES:
                    retry_after = e.headers.get("Retry-After")
                    wait = int(retry_after) if retry_after else INITIAL_BACKOFF * (2 ** attempt)
                    print(f"  Retrying in {wait}s (HTTP {e.code})...", file=sys.stderr)
                    time.sleep(wait)
                    continue
                body = e.read().decode("utf-8", errors="replace")
                print(f"ERROR: Failed to fetch comments — HTTP {e.code}\n{body}", file=sys.stderr)
                sys.exit(1)

        total_count = data.get("totalCount", len(all_comments))
        comments = data.get("comments", [])
        if not comments:
            break

        for c in comments:
            if len(all_comments) >= max_comments:
                break
            all_comments.append({
                "id": c.get("id"),
                "author": c.get("createdBy", {}).get("displayName", "Unknown"),
                "date": c.get("createdDate", ""),
                "text": c.get("text", ""),
            })

        continuation_token = data.get("continuationToken")
        if not continuation_token:
            break

    return {
        "workItemId": work_item_id,
        "totalCount": total_count,
        "fetchedCount": len(all_comments),
        "comments": all_comments,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Fetch comments from an Azure DevOps work item."
    )
    parser.add_argument("--work-item-id", required=True, type=int, help="Work item ID")
    parser.add_argument("--org", required=True, help="Azure DevOps organization URL")
    parser.add_argument("--project", required=True, help="Azure DevOps project name")
    parser.add_argument(
        "--max-comments", type=int, default=DEFAULT_MAX_COMMENTS,
        help=f"Maximum number of comments to fetch (default: {DEFAULT_MAX_COMMENTS})"
    )

    args = parser.parse_args()
    auth_scheme, auth_value = get_token()

    result = fetch_comments(
        args.org, args.project, args.work_item_id,
        args.max_comments, auth_scheme, auth_value
    )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
