#!/usr/bin/env python3
"""
Azure DevOps Work Item — Comment Poster

Posts a markdown comment to a work item's discussion thread via the REST API.
Reads the comment body from a file to avoid shell quoting issues with large
markdown content.

Usage:
    python azdo-add-comment.py \\
        --work-item-id 12345 \\
        --org "https://dev.azure.com/myorg" \\
        --project "MyProject" \\
        --file comment.md

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

API_VERSION = "7.1-preview.4"
ADO_RESOURCE_ID = "499b84ac-1321-427f-aa17-267ca6975798"
MAX_RETRIES = 3
INITIAL_BACKOFF = 2


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


def post_comment(org_url, project, work_item_id, comment_text, auth_scheme, auth_value):
    """Post a comment to a work item's discussion thread."""
    org = org_url.rstrip("/")
    proj = urllib.parse.quote(project, safe="")
    url = f"{org}/{proj}/_apis/wit/workItems/{work_item_id}/comments?api-version={API_VERSION}"

    payload = json.dumps({"text": comment_text}).encode("utf-8")
    ctx = ssl.create_default_context()

    for attempt in range(MAX_RETRIES + 1):
        req = urllib.request.Request(url, data=payload, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", f"{auth_scheme} {auth_value}")

        try:
            resp = urllib.request.urlopen(req, context=ctx)
            return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            if e.code in (429, 502, 503, 504) and attempt < MAX_RETRIES:
                retry_after = e.headers.get("Retry-After")
                wait = int(retry_after) if retry_after else INITIAL_BACKOFF * (2 ** attempt)
                print(f"  Retrying in {wait}s (HTTP {e.code})...", file=sys.stderr)
                time.sleep(wait)
                continue
            print(f"ERROR: Failed to post comment — HTTP {e.code}\n{body}", file=sys.stderr)
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Post a markdown comment to an Azure DevOps work item.")
    parser.add_argument("--work-item-id", required=True, type=int, help="Work item ID")
    parser.add_argument("--org", required=True, help="Azure DevOps organization URL")
    parser.add_argument("--project", required=True, help="Azure DevOps project name")
    parser.add_argument("--file", required=True, help="Path to markdown file containing the comment")
    args = parser.parse_args()

    if not os.path.isfile(args.file):
        print(f"ERROR: Comment file not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    with open(args.file, "r", encoding="utf-8") as fh:
        comment_text = fh.read()

    if not comment_text.strip():
        print("ERROR: Comment file is empty.", file=sys.stderr)
        sys.exit(1)

    auth_scheme, auth_value = get_token()
    result = post_comment(args.org, args.project, args.work_item_id, comment_text, auth_scheme, auth_value)

    output = {
        "workItemId": args.work_item_id,
        "commentId": result.get("id"),
        "createdDate": result.get("createdDate"),
        "url": result.get("url", "")
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
