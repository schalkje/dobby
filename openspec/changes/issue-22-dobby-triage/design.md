# Design: dobby-triage

## Decisions

1. **Two prose variants, combined reuses ado** — same pattern as create/update/propose: the work item system is what's being listed, and in combined mode that's ADO. No seam needed (nothing GitHub-specific to weave in for a read-only listing).
2. **No `_lib` scripts** — `gh issue list --json` and `az boards query --wiql` both return parseable JSON directly; the skill stays pure prose, consistent with "GitHub side has no helper scripts" and with keeping ADO helpers for write-path workarounds only.
3. **Read-only enforced three ways** — a critical rule up top, a rationalization table (the pressure excuse is "close the stale ones while you're at it"), and a handoff section that routes every action to the *owning* skill instead of doing it inline.
4. **Stale = no update in 30 days** — matches dobby-worktree's staleness idea (7 days there is for worktrees; issues linger longer). Displayed as a flag, never acted on.
5. **Default query = open items, newest-updated first, capped at 30** — a triage view, not an export. The cap is stated in output when hit (no silent truncation).
6. **Fragments reused**: `github-prereqs`/`ado-prereqs`, `github-config-example`/`ado-config-example`, `ado-command-rules` — zero new duplicated boilerplate.

## Next-action mapping (both variants)

| Observation about an item | Suggested skill |
|---|---|
| Thin/ambiguous body, missing acceptance criteria | `dobby-update-pbi` (refine) |
| Well-formed, not yet spec'd | `dobby-propose-from-pbi` |
| Spec exists (`openspec/changes/` match) or trivially small | `dobby-implement-pbi` |
| Work appears done (merged PR references it / all criteria checked) | `dobby-close-pbi` |
