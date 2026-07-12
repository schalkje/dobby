# When to Split into a Feature + Multiple PBIs

When creating multiple related PBIs, **always group them under a Feature**. Do not create PBIs under another PBI — that violates ADO hierarchy (see the hierarchy section of the main SKILL.md).

## Decision rules

| Scenario | Action |
|---|---|
| **1 PBI, existing Feature parent** | Create PBI under the Feature |
| **1 PBI, no Feature parent** | Create under existing Feature if one fits, or create standalone |
| **2–3 related PBIs** | Ensure a Feature parent exists; create PBIs as siblings under it |
| **>3 PBIs, or a clear multi-phase deliverable** | Create a new Feature (name: `"<Product> - <Feature Name>"`), parent all PBIs under it |
| **User references an existing PBI** | Inspect its parent chain. If no Feature exists above it, create one and re-parent the existing PBI under it |
| **Mixed scope (refine existing + add new)** | Refine the existing PBI in place, create new sibling PBIs under the same Feature; link with Predecessor/Successor where order matters |

## Execution order

Always confirm the proposed hierarchy with the user via `ask_user` before creating any work items. Show the planned structure. Once confirmed:

1. **Create the Feature** (if needed) — use the two-step process (create + helper script for markdown fields). Link to parent Epic if one exists.
2. **Re-parent existing items** if they need to move under the new Feature.
3. **Create the new PBIs** — use the two-step process for each. Link to Feature as parent.
4. **Link order** via Predecessor/Successor relations where implementation sequence matters.
5. **Cross-reference**: in each work item's description, reference siblings/dependencies as full markdown links (`[#NNNN](url)`) — see `references/markdown-gotchas.md`.
6. **Update the Feature description** to list all child PBIs with links and suggested implementation order.
