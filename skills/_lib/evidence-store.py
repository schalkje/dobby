#!/usr/bin/env python3
"""
Local Evidence Store — manage before/after screenshot storage for work items.

Stores evidence images in `.dobby/evidence/<work-item-id>/<phase>/` where
phase is "before" or "after".

Usage:
    # Store before screenshots
    python evidence-store.py store --work-item-id 12345 --phase before screenshot1.png screenshot2.png

    # Store after screenshots
    python evidence-store.py store --work-item-id 12345 --phase after screenshot1.png

    # List stored evidence for a work item
    python evidence-store.py list --work-item-id 12345

    # List only before images
    python evidence-store.py list --work-item-id 12345 --phase before
"""

import argparse
import json
import os
import shutil
import sys
import time

EVIDENCE_ROOT = ".dobby/evidence"
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}


def get_evidence_dir(work_item_id, phase=None):
    """Return the evidence directory path for a work item and optional phase."""
    base = os.path.join(EVIDENCE_ROOT, str(work_item_id))
    if phase:
        return os.path.join(base, phase)
    return base


def validate_image_file(filepath):
    """Validate that a file exists and is a supported image type."""
    if not os.path.isfile(filepath):
        return False, f"File not found: {filepath}"

    ext = os.path.splitext(filepath)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Unsupported file type '{ext}': {filepath} (supported: {', '.join(sorted(ALLOWED_EXTENSIONS))})"

    return True, None


def generate_unique_name(target_dir, original_name):
    """Generate a unique filename to avoid overwrites."""
    base, ext = os.path.splitext(original_name)
    candidate = original_name
    counter = 1
    while os.path.exists(os.path.join(target_dir, candidate)):
        candidate = f"{base}_{counter}{ext}"
        counter += 1
    return candidate


def cmd_store(args):
    """Store evidence images for a work item."""
    target_dir = get_evidence_dir(args.work_item_id, args.phase)
    os.makedirs(target_dir, exist_ok=True)

    stored = []
    errors = []

    for filepath in args.files:
        valid, error = validate_image_file(filepath)
        if not valid:
            errors.append(error)
            continue

        original_name = os.path.basename(filepath)
        unique_name = generate_unique_name(target_dir, original_name)
        dest = os.path.join(target_dir, unique_name)

        try:
            shutil.copy2(filepath, dest)
            stored.append({
                "source": filepath,
                "stored_as": dest,
                "name": unique_name
            })
        except OSError as e:
            errors.append(f"Failed to copy {filepath}: {e}")

    result = {
        "workItemId": args.work_item_id,
        "phase": args.phase,
        "directory": target_dir,
        "stored": stored,
        "errors": errors
    }
    print(json.dumps(result, indent=2))

    if errors:
        sys.exit(1)


def cmd_list(args):
    """List stored evidence images for a work item."""
    base_dir = get_evidence_dir(args.work_item_id)

    if not os.path.isdir(base_dir):
        result = {
            "workItemId": args.work_item_id,
            "exists": False,
            "before": [],
            "after": []
        }
        print(json.dumps(result, indent=2))
        return

    phases = [args.phase] if args.phase else ["before", "after"]
    evidence = {"workItemId": args.work_item_id, "exists": True}

    for phase in ["before", "after"]:
        phase_dir = os.path.join(base_dir, phase)
        if phase not in phases or not os.path.isdir(phase_dir):
            evidence[phase] = []
            continue

        files = []
        for f in sorted(os.listdir(phase_dir)):
            fpath = os.path.join(phase_dir, f)
            if os.path.isfile(fpath):
                ext = os.path.splitext(f)[1].lower()
                if ext in ALLOWED_EXTENSIONS:
                    files.append({
                        "name": f,
                        "path": fpath,
                        "size": os.path.getsize(fpath)
                    })
        evidence[phase] = files

    print(json.dumps(evidence, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Manage local evidence screenshots for work items.")
    sub = parser.add_subparsers(dest="command", required=True)

    # store
    sp_store = sub.add_parser("store", help="Store evidence images")
    sp_store.add_argument("--work-item-id", required=True, type=int, help="Work item ID")
    sp_store.add_argument("--phase", required=True, choices=["before", "after"], help="Evidence phase")
    sp_store.add_argument("files", nargs="+", help="Image file paths to store")

    # list
    sp_list = sub.add_parser("list", help="List stored evidence")
    sp_list.add_argument("--work-item-id", required=True, type=int, help="Work item ID")
    sp_list.add_argument("--phase", choices=["before", "after"], help="Filter by phase")

    args = parser.parse_args()

    if args.command == "store":
        cmd_store(args)
    elif args.command == "list":
        cmd_list(args)


if __name__ == "__main__":
    main()
