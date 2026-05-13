## ADDED Requirements

### Requirement: Skill fetches a GitHub Issue and generates an OpenSpec change
The `dobby-gh-propose-from-issue` skill SHALL accept an issue identifier (number, `#N` reference, GitHub URL, or title keywords), fetch the issue from the configured repository via `gh`, and generate an OpenSpec change directory seeded from its content.

#### Scenario: Lookup by issue number
- **WHEN** the user provides an issue number or `#N` reference
- **THEN** the skill SHALL fetch the issue via `gh issue view <N> --json title,body,labels,state,url,milestone` and proceed to generate the OpenSpec change

#### Scenario: Lookup by URL
- **WHEN** the user provides a GitHub issue URL
- **THEN** the skill SHALL extract the issue number from the URL and proceed as above

#### Scenario: Lookup by keyword search
- **WHEN** the user provides keywords instead of a number
- **THEN** the skill SHALL search via `gh issue list --search "<keywords>" --json number,title,state` and ask the user to confirm the match before fetching its full content

### Requirement: Change directory name encodes the issue number
The skill SHALL name the generated OpenSpec change directory `issue-<N>-<slug>` where `<N>` is the GitHub issue number and `<slug>` is a kebab-case truncation of the issue title.

#### Scenario: Directory naming
- **WHEN** the skill generates a change from issue `#42` titled "Add dark mode toggle"
- **THEN** the directory SHALL be created at `openspec/changes/issue-42-add-dark-mode-toggle/`

#### Scenario: Title slug truncation
- **WHEN** the issue title is long enough that `issue-<N>-<full-slug>` would exceed 50 characters
- **THEN** the slug SHALL be truncated at a word boundary to keep the directory name within a reasonable length

### Requirement: Source traceability recorded in the proposal
The skill SHALL include a "Source" line at the top of the generated `proposal.md` linking back to the GitHub issue.

#### Scenario: Source line written
- **WHEN** the skill writes `proposal.md`
- **THEN** the file SHALL include a blockquote at the top of the form `> Source: GitHub Issue [#<N>](<url>) — "<title>"`

### Requirement: Skill optionally posts a back-link comment on the issue
The skill SHALL offer (but not require) to post a comment on the source issue noting that an OpenSpec change has been created and naming the change directory.

#### Scenario: User opts in to back-link
- **WHEN** the skill has successfully created the change and the user opts in to back-linking
- **THEN** the skill SHALL post a comment via `gh issue comment <N>` containing the change name and a one-line summary

#### Scenario: User opts out
- **WHEN** the user declines the back-link prompt
- **THEN** the skill SHALL skip the comment and the issue SHALL remain unchanged

### Requirement: Skill validates prerequisites
The skill SHALL verify that `gh` is installed and authenticated, that the `openspec` CLI is available, and that the configured repository is accessible before doing real work.

#### Scenario: openspec CLI missing
- **WHEN** the `openspec` command is not available on the system PATH
- **THEN** the skill SHALL stop and instruct the user to install it before re-running

#### Scenario: gh auth or repo access failure
- **WHEN** `gh auth status` or `gh repo view <owner>/<repo>` fails
- **THEN** the skill SHALL stop and report the failure with the resolved repo coordinates

### Requirement: Skill generates OpenSpec artifacts in dependency order
The skill SHALL follow the OpenSpec CLI's `openspec status --json` dependency information to generate artifacts (proposal, design, specs, tasks) in an order that respects each artifact's `applyRequires` and dependency list.

#### Scenario: Proposal generated first, then dependents
- **WHEN** the skill begins generation
- **THEN** it SHALL write `proposal.md` before reading instructions for `design.md`, `specs/`, or `tasks.md`, since the latter three depend on the proposal

#### Scenario: Issue content injected as primary context
- **WHEN** the skill writes any artifact
- **THEN** the GitHub issue's title, body, and labels SHALL be used as the primary context source for that artifact, with the artifact's `template` and `rules` constraining the structure
