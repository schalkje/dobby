### ⛔ Command Execution Rules

- **No piping.** Every `az` and `python` command in this skill is designed to be run standalone with `--output json`. Do NOT append any pipe (`|`) to transform, filter, or format the output — no `| ConvertFrom-Json`, `| Select-Object`, `| jq`, `| python -c "..."`, `| grep`, or any other pipe. Read the full JSON output and extract fields in your own reasoning.
- **Resolve bundled files relative to the installed skill set.** Scripts ship under their owning skill's `scripts/` folder — e.g., `python skills/_lib/azdo-update-fields.py` — and templates under their owning skill's `templates/` folder. Never reach back into dobby's source repository for them.
