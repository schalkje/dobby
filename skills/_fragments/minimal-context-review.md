### Dispatching review work (when the host supports subagents)

- **Pass artifacts as file paths, not pasted text** — pasted content stays resident in context for the rest of the session. Write the item under review (issue body, proposal, diff) to a file and hand over the path.
- **Give the reviewer minimal context**: only the artifact plus the spec/constraints it must be judged against — never the conversation history. A reviewer that sees the whole conversation role-plays as the author. Do include the actual spec: a reviewer given only a diff silently redefines "spec" as whatever the diff implies.
- **Never instruct a reviewer to ignore or not flag a specific issue.**
- **Match model to task**: use a capable model for review and architecture judgments; mechanical work (formatting, evidence collection) can go to a cheaper one.
