# Architecture Decisions

Lightweight decision log for key Dobby architecture choices. Captures the "why" behind patterns that might otherwise seem arbitrary.

---

## 1. Dobby is a skill library, not an application

**Status:** Accepted

**Context:** Dobby needs to work across multiple AI coding assistants (Copilot CLI, Claude Code). Building a standalone application would require its own runtime and integration layer.

**Decision:** Dobby is a collection of skill definitions (SKILL.md files + helper scripts) that AI hosts discover and execute natively.

**Consequences:** No build/test pipeline. Quality comes from prompt design and manual smoke testing. Skills must be self-contained enough for any compatible host to execute.

---

## 2. Canonical source with generated host copies

**Status:** Accepted

**Context:** Copilot CLI discovers skills under `.github/skills/` and Claude Code under `.claude/skills/`. Maintaining three copies manually would drift.

**Decision:** `skills/` is the single source of truth. `sync-skills.py` generates the host copies. `check-skill-sync.py` verifies no drift.

**Consequences:** Contributors must run the sync script before committing. Generated folders should never be edited directly. Copying (not symlinking) is used for Windows compatibility and to avoid host-specific path resolution issues.

---

## 3. Dispatcher → backend separation

**Status:** Accepted

**Context:** Dobby supports two trackers (ADO, GitHub) with different APIs, CLIs, and idioms. Users should not need to know which backend commands to invoke.

**Decision:** Public-facing "dispatcher" skills route based on `.dobby/config.json`. Backend-specific skills contain all API/CLI logic. Dispatchers never call tracker APIs directly.

**Consequences:** Adding a new operation requires a dispatcher + one backend skill per supported tracker. User-facing skill names stay stable regardless of backend. Each backend follows its tracker's native patterns rather than forcing symmetry.

---

## 4. Only Azure DevOps and GitHub

**Status:** Accepted

**Context:** Jira, Linear, GitLab, and other trackers exist. Supporting them all would dilute focus.

**Decision:** Support only ADO and GitHub. The dispatcher pattern makes adding backends mechanically possible, but it's not a goal.

**Consequences:** Backend skills can use ADO/GitHub-specific patterns freely without worrying about lowest-common-denominator abstractions.

---

## 5. Each backend follows its native idiom

**Status:** Accepted

**Context:** ADO and GitHub have fundamentally different models (ADO: work items, hierarchy, separate fields; GitHub: issues, PRs, flat labels, single body). Forcing symmetry would produce a leaky abstraction.

**Decision:** Each backend does things "the GitHub way" or "the ADO way":
- ADO: two-step creation, REST helper scripts, direct state changes
- GitHub: PR-based closure, committed evidence, task-list parent linkage

**Consequences:** Backend skills are not interchangeable templates — each is purpose-built. Cross-backend invariants (JSON output, identity check, no auto-retry) provide consistency without forcing identical flows.

---

## 6. OpenSpec is bundled but conceptually separate

**Status:** Accepted

**Context:** OpenSpec is an external tool with its own release cycle. Dobby wraps it for workflow convenience but doesn't own it.

**Decision:** OpenSpec wrapper skills call the `openspec` CLI but never modify its config or internals. OpenSpec updates are independent of Dobby updates.

**Consequences:** If the OpenSpec CLI changes its interface, wrapper skills need updating. But Dobby never pins or distributes an OpenSpec version.

---

## 7. Conversational skill variations are separate skills

**Status:** Accepted

**Context:** `grill-me` may need domain-specific variations (security, architecture, cost, etc.). These could be modes in one skill or separate skills.

**Decision:** Each variation is a separate skill with its own `SKILL.md`. This keeps them independently discoverable, focused, and easy to evolve.

**Consequences:** More skill folders, but each is self-contained. No parameter parsing or mode-switching logic inside a single skill prompt. Naming and discovery rely on good `description` fields in frontmatter.

---

## 8. Python helpers use stdlib only

**Status:** Accepted

**Context:** ADO helper scripts need HTTP, JSON, and auth. Adding pip dependencies would require a virtual environment and dependency management.

**Decision:** All Python helper scripts use only the standard library. No `requirements.txt`, no `pip install`.

**Consequences:** HTTP calls use `urllib` instead of `requests`. No third-party libraries for convenience. Keeps the library zero-dependency beyond the CLIs.

---

## 9. No versioning — latest is best

**Status:** Accepted

**Context:** Skills are prompts, not APIs. There are no consumers that depend on a specific skill version.

**Decision:** No version numbers on skills. The latest commit is always the current version.

**Consequences:** Breaking changes to a skill prompt are simply committed. No migration path needed. Git history serves as the version record if rollback is needed.

---

## 10. `.dobby/evidence/` is gitignored

**Status:** Accepted

**Context:** ADO before/after screenshots may contain sensitive data (customer information, internal dashboards).

**Decision:** Local evidence is staged under `.dobby/evidence/` which is gitignored. It's uploaded to ADO as attachments but never committed to the repository.

**Consequences:** Evidence is ephemeral on the developer's machine. ADO work items hold the permanent copy. GitHub evidence follows a different path — committed to PR branches under `docs/evidence/issue-<N>/` because GitHub needs committed files for inline rendering.
