# Intended scenario asymmetries (ADO vs GitHub)

The `ado` and `github` skill sets deliberately do **not** mirror each other. Each scenario follows
its tracker's native idiom instead of forcing symmetry, and several "inconsistencies" between the
two flows are design decisions. Before "fixing" a difference between `skills/ado/` and
`skills/github/`, check this list.

## Intended differences (do not reconcile)

### 1. Evidence flow

- **ADO**: before/after screenshots are uploaded as **work-item attachments** and posted to the
  Discussion thread as markdown comments. Local staging lives under `tests/e2e/evidence/` or
  `.dobby/evidence/` and is **gitignored** — ADO captures may contain sensitive data, and once
  uploaded the attachment is the durable copy, so committing the files would be duplication.
- **GitHub**: screenshots are **committed to the PR branch** under `docs/evidence/issue-<N>/` and
  embedded in the PR description via repo-relative paths (rendered through
  `raw.githubusercontent.com`). The directory is deliberately NOT gitignored; the files survive the
  merge and are pruned periodically with housekeeping commits.
- **Combined**: evidence is committed to the GitHub PR branch (`docs/evidence/pbi-<id>/`) *and*
  uploaded to the ADO work item so both surfaces render it inline.

### 2. Closure mechanics

- **ADO**: `dobby-close-pbi` talks to the work item directly — it posts the closing comment, checks
  acceptance criteria, and sets `State = Done`. It is **PR-agnostic**: a PR is linked when one
  exists, but closing does not require one.
- **GitHub**: `dobby-close-pbi` **requires an open PR** whose body references the issue
  (`Closes #N` / `Fixes #N` / `Resolves #N`). The issue closes automatically at PR merge; the skill
  never calls `gh issue close`. This is GitHub's idiomatic workflow, not a missing feature.
- **Combined**: split on purpose — state/comment/AC go to ADO (closed explicitly, since GitHub's
  `Closes` cannot touch an ADO work item), evidence goes to the GitHub PR.

### 3. Work-item typing and hierarchy

- **ADO**: strict `Epic → Feature → PBI → Task` hierarchy, distinct Bug fields
  (`Microsoft.VSTS.TCM.ReproSteps` as the primary field), and three templates
  (`pbi-template.md`, `feature-template.md`, `bug-template.md`) mapping to separate ADO fields.
- **GitHub**: issues are untyped with a **single markdown body**; one template
  (`issue-template.md`) with Description + Acceptance Criteria sections. "Hierarchy" is expressed
  as task-list references (`- [ ] #N`) in a parent issue's body — there is no hard parent link to
  validate, so the github create skill has no hierarchy decision table. Don't add one.

### 4. Development links

- **ADO**: commit/branch/PR links are attached via `azdo-add-dev-links.py`, choosing
  ArtifactLink vs Hyperlink based on whether the org's ADO can reach the repo (the
  `ado.devLinks` config block — canonical explanation in `skills/_fragments/ado-dev-links.md`).
- **GitHub**: no equivalent step exists because none is needed — `#N` references, `Closes #N`,
  and PR branches are natively cross-linked by GitHub itself.

### 5. Helper scripts

- **ADO**: Python REST helpers (`skills/_lib/azdo-*.py`) exist because `az boards` truncates
  multiline fields, cannot set the Markdown format flag, and the comments API silently downgrades
  markdown to HTML. Do not "simplify" them away.
- **GitHub**: zero helper scripts, by design — `gh issue create --body-file`, `gh issue edit`,
  `gh pr edit` handle everything, and GitHub renders markdown natively. Do not add Python
  intermediaries for symmetry.

## Accidental differences (tracked for reconciliation — see issue #9)

These gaps are historical, not intended, and are candidates to add to the github flow:

- **No git-history / OpenSpec evidence gathering in github close**: the ADO close flow harvests
  `git log --grep=<id>`, the OpenSpec change directory (`proposal.md` / `tasks.md` status), and
  test results as closing evidence; the github close flow only handles screenshots and a
  user-provided summary.
- **No child-task closure step in github close**: the ADO close flow lists child Tasks and offers
  to close them with the PBI; the github flow has no equivalent sweep of task-list-referenced
  sub-issues.
