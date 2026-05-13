## ADDED Requirements

### Requirement: Closing flow requires an open Pull Request
The `dobby-gh-close-issue` skill SHALL refuse to proceed unless an open Pull Request references the target issue. The reference SHALL be detected via a `Closes #<N>`, `Fixes #<N>`, or `Resolves #<N>` directive in the PR body, or via GitHub's linked-issue relationship.

#### Scenario: PR exists and references the issue
- **WHEN** the user invokes the closing flow for issue `#42` and an open PR contains `Closes #42` in its body or is linked to `#42` via the GitHub UI
- **THEN** the skill SHALL identify that PR as the closure vehicle and continue with evidence gathering

#### Scenario: No PR references the issue
- **WHEN** the user invokes the closing flow for an issue and no open PR references it
- **THEN** the skill SHALL stop, report "No PR references issue #<N>. Create one with `Closes #<N>` in the body and re-run.", and SHALL NOT modify any state

#### Scenario: Multiple PRs reference the issue
- **WHEN** more than one open PR references the issue
- **THEN** the skill SHALL list the candidate PRs with their numbers and titles and ask the user to confirm which one is the closure vehicle

### Requirement: Evidence committed to the PR branch
The skill SHALL place screenshot evidence as image files in the repository under `docs/evidence/issue-<N>/` and commit them to the PR branch. Image filenames SHALL distinguish before/after state (e.g., `before-*.png`, `after-*.png`).

#### Scenario: Playwright-generated screenshots committed
- **WHEN** the project supports Playwright-based evidence generation and the skill runs the supporting spec
- **THEN** the resulting PNGs SHALL be written to `docs/evidence/issue-<N>/` on the current branch, staged, committed with a clear message, and pushed to origin

#### Scenario: User-supplied screenshots committed
- **WHEN** the user provides file paths to pre-captured screenshots
- **THEN** the skill SHALL copy those files into `docs/evidence/issue-<N>/`, stage, commit, and push them to the PR branch

#### Scenario: Existing evidence directory respected
- **WHEN** `docs/evidence/issue-<N>/` already contains screenshots from a prior invocation
- **THEN** new captures SHALL be added alongside existing files without overwriting, using filename suffixes to disambiguate if necessary

### Requirement: PR description embeds evidence inline
The skill SHALL update the PR description to embed the screenshot files inline as markdown image references using paths relative to the repository root. The description SHALL also include a `Closes #<N>` directive if one is not already present.

#### Scenario: PR description updated with evidence and closure directive
- **WHEN** the skill has committed evidence files and the PR description does not yet reference them
- **THEN** the skill SHALL update the PR description to include a "Before" section and an "After" section with `![alt](docs/evidence/issue-<N>/<filename>)` references, and ensure the description contains `Closes #<N>`

#### Scenario: Closing directive already present
- **WHEN** the PR body already contains `Closes #<N>`, `Fixes #<N>`, or `Resolves #<N>` for the target issue
- **THEN** the skill SHALL NOT duplicate the directive

#### Scenario: Description preserves existing prose
- **WHEN** the PR description has user-authored content
- **THEN** the skill SHALL preserve that content and append the evidence sections beneath it, rather than replacing the body wholesale

### Requirement: Issue closure delegated to PR merge
The skill SHALL NOT call `gh issue close` directly. Issue closure SHALL happen automatically when the referencing PR is merged via GitHub's native `Closes #<N>` mechanic.

#### Scenario: Skill completes without closing the issue
- **WHEN** the skill finishes its flow
- **THEN** the target issue SHALL still be open and the skill SHALL inform the user that closure will happen when the PR merges

#### Scenario: Optional closing comment on the issue
- **WHEN** the user opts in to a closing comment on the issue
- **THEN** the skill SHALL post a brief comment to the issue summarizing the work and linking to the PR, but SHALL still leave issue closure to PR merge

### Requirement: Skill validates prerequisites
The skill SHALL verify that `gh` is installed and authenticated, that the working tree is clean enough to commit evidence, and that the PR branch is pushed to origin before posting URLs.

#### Scenario: Working tree has uncommitted unrelated changes
- **WHEN** the working tree contains uncommitted changes outside `docs/evidence/issue-<N>/`
- **THEN** the skill SHALL warn the user and ask whether to proceed (committing only the evidence files) or stop

#### Scenario: Branch not pushed
- **WHEN** the local PR branch is ahead of `origin/<branch>` after the evidence commit
- **THEN** the skill SHALL push to origin before updating the PR description, so the embedded image URLs resolve immediately for reviewers

### Requirement: Skill reports closure outcome
The skill SHALL display a summary of what was done, including the PR number, the evidence files committed, and a note that issue closure will occur on PR merge.

#### Scenario: Successful closure flow output
- **WHEN** the skill completes without errors
- **THEN** the skill outputs the issue number, PR number, list of evidence files committed, the PR URL, and a clear note that issue `#<N>` will close automatically when the PR merges
