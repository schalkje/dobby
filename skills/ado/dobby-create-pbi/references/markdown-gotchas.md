# Markdown Gotchas (ADO multiline fields)

When generating markdown content for `System.Description`, `Microsoft.VSTS.Common.AcceptanceCriteria`, or `Microsoft.VSTS.TCM.ReproSteps`, follow these rules — they are non-obvious failure modes that produce broken-looking content in ADO:

1. **Content must be Markdown, never HTML.** Do not use `<b>`, `<br>`, `<ul>`, `<li>`, `<div>`, or any HTML tags. When the helper script sets the field format to Markdown, any HTML tags will render as raw escaped text (e.g., users see literal `<b>Goal:</b>` instead of **Goal:**). Use markdown: `**bold**`, `- list items`, blank lines for paragraphs, `---` for horizontal rules.
   - ❌ `<b>Goal:</b><br><ul><li>Item one</li></ul>`
   - ✅ `**Goal:**\n\n- Item one`

2. **`#NNNN` does NOT autolink in rendered markdown.** Azure DevOps autolinks `#NNNN` in plain-text comments, but in **markdown-formatted description / AC fields it does not**. Always use a full link:
   - ❌ `See #1021105 for the foundation.`
   - ✅ `See [#1021105](https://dev.azure.com/<org>/<project>/_workitems/edit/1021105) for the foundation.`
   - This applies in tables, bullet lists, and prose. Apply it to **every** work item reference, including the parent and any sibling/dependency references.

3. **Code blocks suppress markdown link rendering.** ASCII diagrams or fenced code blocks hide any `[text](url)` links inside. If you want a hierarchy or order diagram with clickable links, use a **markdown bullet tree** instead of a code block:
   - ❌ ```\n#1021105 → #1021174\n```  (links won't render)
   - ✅ Bulleted tree with explicit `[#NNNN](url)` per node

4. **Field format defaults to HTML.** When updating fields via `az boards work-item update --fields "..."` or via raw REST `PATCH` without setting `multilineFieldsFormat`, ADO renders the content as HTML — escaping markdown syntax. **Always use the helper script** (which sets format = Markdown) for any multiline field write — both on create and on update.

5. **`az boards work-item update --description "..."` truncates at the first newline.** The same limitation that applies to `create`. Never use it for multiline content. Use the helper script instead.
