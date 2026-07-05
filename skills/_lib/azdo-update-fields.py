#!/usr/bin/env python3
"""
Azure DevOps Work Item — Markdown Field Updater

Sets multiline fields on an Azure DevOps work item to Markdown format
and updates their content. Uses the REST API because the `az boards` CLI
truncates multiline content at newlines and cannot change field format.

Usage:
    python azdo-update-fields.py \\
        --work-item-id 12345 \\
        --org "https://dev.azure.com/myorg" \\
        --project "MyProject" \\
        --field System.Description=description.md \\
        --field Microsoft.VSTS.Common.AcceptanceCriteria=ac.md

Each --field maps an Azure DevOps field reference name to a local Markdown
file whose content will be written into that field.

Authentication (tried in order):
    1. AZURE_DEVOPS_EXT_PAT environment variable (PAT)
    2. ADO_TOKEN environment variable (Bearer token)
    3. `az account get-access-token` (AAD — requires Azure CLI)
"""

import argparse
import json
import os
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API_VERSION = "7.1"
ADO_RESOURCE_ID = "499b84ac-1321-427f-aa17-267ca6975798"
MAX_RETRIES = 3
INITIAL_BACKOFF = 2  # seconds


def get_token():
    """Get an authentication token, trying multiple methods."""
    # 1. PAT via environment variable
    pat = os.environ.get("AZURE_DEVOPS_EXT_PAT")
    if pat:
        import base64
        encoded = base64.b64encode(f":{pat}".encode()).decode()
        return "Basic", encoded

    # 2. Pre-set bearer token
    token = os.environ.get("ADO_TOKEN")
    if token:
        return "Bearer", token

    # 3. Azure CLI
    try:
        # On Windows, az is a .cmd — need shell=True
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


def build_url(org_url, project, work_item_id):
    """Build a properly encoded REST API URL."""
    org = org_url.rstrip("/")
    proj = urllib.parse.quote(project, safe="")
    return f"{org}/{proj}/_apis/wit/workitems/{work_item_id}?api-version={API_VERSION}"


def do_request(url, patch_ops, auth_scheme, auth_value):
    """Execute a PATCH request with retry and backoff."""
    data = json.dumps(patch_ops).encode("utf-8")
    ctx = ssl.create_default_context()

    for attempt in range(MAX_RETRIES + 1):
        req = urllib.request.Request(url, data=data, method="PATCH")
        req.add_header("Content-Type", "application/json-patch+json")
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
            print(f"ERROR: HTTP {e.code}\n{body}", file=sys.stderr)
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Update Azure DevOps work item fields as Markdown."
    )
    parser.add_argument("--work-item-id", required=True, type=int,
                        help="Work item ID to update")
    parser.add_argument("--org", required=True,
                        help="Azure DevOps organization URL")
    parser.add_argument("--project", required=True,
                        help="Azure DevOps project name")
    parser.add_argument("--field", action="append", required=True,
                        metavar="FIELD_REF=FILE",
                        help="Field reference name and markdown file path (repeatable)")
    args = parser.parse_args()

    # Parse field arguments
    fields = {}
    for f in args.field:
        if "=" not in f:
            print(f"ERROR: Invalid --field format: {f}", file=sys.stderr)
            print("  Expected: FieldReferenceName=path/to/file.md", file=sys.stderr)
            sys.exit(1)
        ref, path = f.split("=", 1)
        if not os.path.isfile(path):
            print(f"ERROR: File not found: {path}", file=sys.stderr)
            sys.exit(1)
        with open(path, "r", encoding="utf-8") as fh:
            fields[ref] = fh.read()

    # Authenticate
    auth_scheme, auth_value = get_token()

    # Build PATCH operations — use "add" (works whether field exists or not)
    patch_ops = []
    for ref, content in fields.items():
        patch_ops.append({"op": "add", "path": f"/fields/{ref}", "value": content})
        patch_ops.append({"op": "add", "path": f"/multilineFieldsFormat/{ref}", "value": "Markdown"})

    # Execute
    url = build_url(args.org, args.project, args.work_item_id)
    result = do_request(url, patch_ops, auth_scheme, auth_value)

    # Output
    fmt = result.get("multilineFieldsFormat", {})
    work_item_id = result["id"]
    title = result["fields"].get("System.Title", "")
    org = args.org.rstrip("/")
    proj = urllib.parse.quote(args.project, safe="")
    item_url = f"{org}/{proj}/_workitems/edit/{work_item_id}"

    output = {
        "id": work_item_id,
        "title": title,
        "url": item_url,
        "fieldsUpdated": list(fields.keys()),
        "fieldFormats": fmt
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
