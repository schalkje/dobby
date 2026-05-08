#!/usr/bin/env python3
"""
Azure DevOps Attachment Uploader

Uploads image files to Azure DevOps via the Attachments API and attaches
them to a work item. Returns the attachment URLs for embedding in comments.

Usage:
    python azdo-upload-attachment.py \\
        --work-item-id 12345 \\
        --org "https://dev.azure.com/myorg" \\
        --project "MyProject" \\
        image1.png image2.jpg

    # Dry-run mode (validates without uploading)
    python azdo-upload-attachment.py \\
        --work-item-id 12345 \\
        --org "https://dev.azure.com/myorg" \\
        --project "MyProject" \\
        --dry-run \\
        image1.png

Authentication (tried in order):
    1. AZURE_DEVOPS_EXT_PAT environment variable (PAT)
    2. ADO_TOKEN environment variable (Bearer token)
    3. `az account get-access-token` (AAD — requires Azure CLI)
"""

import argparse
import base64
import json
import mimetypes
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
INITIAL_BACKOFF = 2

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
MAX_FILE_SIZE_MB = 130  # Azure DevOps attachment limit


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


def validate_file(filepath):
    """Validate file exists, is an image, and within size limits."""
    if not os.path.isfile(filepath):
        return False, f"File not found: {filepath}"

    ext = os.path.splitext(filepath)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Unsupported file type '{ext}': {filepath} (supported: {', '.join(sorted(ALLOWED_EXTENSIONS))})"

    size_mb = os.path.getsize(filepath) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        return False, f"File too large ({size_mb:.1f} MB, max {MAX_FILE_SIZE_MB} MB): {filepath}"

    return True, None


def upload_attachment(org_url, project, filename, file_data, auth_scheme, auth_value):
    """Upload a file to Azure DevOps Attachments API."""
    org = org_url.rstrip("/")
    encoded_name = urllib.parse.quote(filename)
    url = f"{org}/{urllib.parse.quote(project, safe='')}/_apis/wit/attachments?fileName={encoded_name}&api-version={API_VERSION}"

    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    ctx = ssl.create_default_context()

    for attempt in range(MAX_RETRIES + 1):
        req = urllib.request.Request(url, data=file_data, method="POST")
        req.add_header("Content-Type", content_type)
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
            print(f"ERROR: Upload failed for {filename} — HTTP {e.code}\n{body}", file=sys.stderr)
            return None


def attach_to_work_item(org_url, project, work_item_id, attachment_url, filename, auth_scheme, auth_value):
    """Attach an uploaded file to a work item via JSON Patch."""
    org = org_url.rstrip("/")
    proj = urllib.parse.quote(project, safe="")
    url = f"{org}/{proj}/_apis/wit/workitems/{work_item_id}?api-version={API_VERSION}"

    patch_ops = [{
        "op": "add",
        "path": "/relations/-",
        "value": {
            "rel": "AttachedFile",
            "url": attachment_url,
            "attributes": {
                "comment": f"Evidence: {filename}"
            }
        }
    }]

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
            print(f"ERROR: Attach failed for {filename} — HTTP {e.code}\n{body}", file=sys.stderr)
            return None


def main():
    parser = argparse.ArgumentParser(description="Upload images to Azure DevOps and attach to a work item.")
    parser.add_argument("--work-item-id", required=True, type=int, help="Work item ID to attach images to")
    parser.add_argument("--org", required=True, help="Azure DevOps organization URL")
    parser.add_argument("--project", required=True, help="Azure DevOps project name")
    parser.add_argument("--dry-run", action="store_true", help="Validate files without uploading")
    parser.add_argument("files", nargs="+", help="Image file paths to upload")
    args = parser.parse_args()

    # Validate all files first
    valid_files = []
    errors = []
    for filepath in args.files:
        ok, error = validate_file(filepath)
        if ok:
            valid_files.append(filepath)
        else:
            errors.append(error)
            print(f"WARNING: {error}", file=sys.stderr)

    if not valid_files:
        print(json.dumps({"uploaded": [], "errors": errors}))
        sys.exit(1)

    if args.dry_run:
        result = {
            "dryRun": True,
            "valid": [{"file": f, "size": os.path.getsize(f)} for f in valid_files],
            "errors": errors
        }
        print(json.dumps(result, indent=2))
        return

    auth_scheme, auth_value = get_token()

    uploaded = []
    for filepath in valid_files:
        filename = os.path.basename(filepath)
        with open(filepath, "rb") as fh:
            file_data = fh.read()

        print(f"  Uploading {filename}...", file=sys.stderr)
        upload_result = upload_attachment(args.org, args.project, filename, file_data, auth_scheme, auth_value)

        if not upload_result:
            errors.append(f"Upload failed: {filepath}")
            continue

        attachment_url = upload_result.get("url", "")

        # Attach to work item
        attach_result = attach_to_work_item(
            args.org, args.project, args.work_item_id,
            attachment_url, filename, auth_scheme, auth_value
        )

        if not attach_result:
            errors.append(f"Attach failed (uploaded but not linked): {filepath}")

        uploaded.append({
            "file": filepath,
            "name": filename,
            "url": attachment_url,
            "attached": attach_result is not None
        })

    result = {
        "workItemId": args.work_item_id,
        "uploaded": uploaded,
        "errors": errors
    }
    print(json.dumps(result, indent=2))

    if errors and not uploaded:
        sys.exit(1)


if __name__ == "__main__":
    main()
