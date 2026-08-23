Azure DevOps runs a per-change **DORA for DevOps** risk assessment on PBIs, and its scope is driven entirely by the `Change` tag (`System.Tags` contains `Change` → `Custom.DoraInScope`, which makes the DORA form group appear).

When creating a work item, decide whether it represents a **significant IT change**:

| Situation | Action |
|---|---|
| Code changes, changed scripts, relevant technical or configuration changes | Propose the `Change` tag and add it alongside the other tags |
| Investigation/spike, documentation-only, onboarding, other non-technical activity, manual data entry, data updates using **unchanged** reusable scripts | Do not tag; say briefly why it is out of DORA scope |
| Cannot tell from the description | Ask whether code, scripts, configuration, authentication, data processing, or runtime behaviour change. Never classify from the title alone |

Tagging is the only scope action taken at creation — **do not score, and do not write any `Custom.Dora*` field here.** The assessment itself belongs to refinement, where the description is complete enough to reason over; point the user at the refine/update flow for it. A `bypass` tag may exist in the organization: read it if present, never set it.
