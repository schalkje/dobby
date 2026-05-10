let's do this project using openspec  
the dobby Project is about working with Azure Devops it's about creating new Pbis from short descriptions. I want to be able to give you a description an email and that you create Apbiumm there should be a creation of tasksI want some kind of refinement sessions where wetogether refine the PBI to make a comprehensivepiece of workUmm that we create tasks out of itUmm so we will have multiple processes umm like the PO creating the initial PBIthe refinement session together with the theme and then the implementation planning by the developerand then implementing and during implementation it would be nice if the developer is held with closing down tasks and getting in the testing evidence and that kind of stuffI have no idea about the user interface yetBut it should be easily accessibleIt should be clear it should be interactivePreferable it should useAzure Github copilotand to run the AI

So maybe we need to look into some skillUmm maybe we should have some skill tricking a user interface I don't know if that's possibleOK let's do some more brainstorming

## New PBI's

|ID          | Title |
|------------|---|
| 1021102     | Add 'Add New Relation' option in entity view                                 |
| 1021103     | Highlight newly added attributes in entity edit view                         |
| 1021104     | Fix legend and mini map overlap in diagram view                              |
| 1021105     | Add tabbed navigation for switching between diagrams                         |
| 1021106     | Improve diagram creation flow and fix recent diagrams auto-refresh           |
| 1021107     | Investigate and fix translation inconsistencies from PowerDesigner migration |
| 1021108     | Clarify language toggle UX and remove code field from entities/attributes    |
| 1021109     | Add find/search functionality within diagram view  |





When closing I want evidence of the change added; when possible and applicable I like screen shots of the changes; to make this valueble it might be necessary to create screenshots of the before situation.
I don't know what the bast place is to store this, but I think it is in the comments.

Please also use markdown text and images for the comment fields.

## Lessons Learned — 2026-05-10 (PBI 1021105 refinement session)

Real-world session that exercised the dobby-create-pbi skill across refinement (one PBI expanded into a Feature + 4 PBIs). Captured for backlog into the next round of skill improvements.

### Skill-level findings (already addressed in `dobby-create-pbi` v1.6)

- **`#NNNN` does not autolink in markdown-rendered description / AC** in Azure DevOps. Must use `[#NNNN](url)` everywhere. Added "Markdown Gotchas" section to SKILL.md.
- **Code blocks suppress markdown links** — ASCII tree diagrams hide `[text](url)`. Use a markdown bullet tree instead.
- **Field format defaults to HTML** when set via `az boards` or raw REST `PATCH` without `multilineFieldsFormat`. The helper script must be used for **every** multiline write — create AND update.
- **`az boards work-item update --description "..."` corrupts multiline content** the same way create does. Documented in SKILL.md.
- **Updating existing PBIs** is now documented (re-parent, predecessor/successor, field updates).
- **When to create a Feature vs flat PBIs** — heuristic added (>3 child items → propose sub-feature with naming `"<Project> - <Feature Name>"`).

### Open backlog items (candidate skills / improvements)

- [ ] **`dobby-create-feature` skill** — Create Features (not PBIs). Should reuse the same field-update helper script. Sub-feature naming convention should match the parent project.
- [ ] **`dobby-update-pbi` skill** (or `dobby-refine-pbi`) — Dedicated skill for refining an existing PBI: update title/description/AC (always via helper script), re-parent, add/remove relations. Currently spread across the create-pbi SKILL.md "Updating" section.
- [ ] **`dobby-split-pbi` skill** — Wraps the "expand a request into Feature + multiple PBIs" workflow: confirm hierarchy with user, create feature, refine existing PBI, create siblings, link order. Composition of the above three skills.
- [ ] **Helper script enhancement**: accept inline string content (`--field "Ref=@string:..."`) so callers don't have to write temp files for short content. Optional.
- [ ] **Defaults file**: also store `defaultParentFeature` for quick PBI creation in active features.
