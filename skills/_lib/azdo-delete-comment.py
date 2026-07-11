#!/usr/bin/env python3
"""Delete a comment on an Azure DevOps work item."""
import argparse, base64, os, ssl, subprocess, sys, urllib.error, urllib.request

API_VERSION = "7.2-preview.4"
ADO_RESOURCE_ID = "499b84ac-1321-427f-aa17-267ca6975798"


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


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--work-item-id", required=True, type=int)
    p.add_argument("--comment-id", required=True, type=int)
    p.add_argument("--org", required=True)
    p.add_argument("--project", required=True)
    a = p.parse_args()
    scheme, val = get_token()
    url = f"{a.org.rstrip('/')}/{a.project}/_apis/wit/workItems/{a.work_item_id}/comments/{a.comment_id}?api-version={API_VERSION}"
    req = urllib.request.Request(url, method="DELETE")
    req.add_header("Authorization", f"{scheme} {val}")
    try:
        resp = urllib.request.urlopen(req, context=ssl.create_default_context())
        print(f"Deleted comment {a.comment_id} (HTTP {resp.status})")
    except urllib.error.HTTPError as e:
        print(f"ERROR HTTP {e.code}: {e.read().decode('utf-8', errors='replace')}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
