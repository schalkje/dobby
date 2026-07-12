## ADDED Requirements

### Requirement: Create worktree for a PBI
The system SHALL provide a `dobby-worktree` skill that creates a git worktree for a given PBI or issue identifier. The worktree SHALL be created in a configurable root directory (default: `<repo-parent>/<repo-name>-worktrees/`) with a directory name derived from the branch name (slashes replaced with hyphens).

#### Scenario: Create worktree for a PBI with default root
- **WHEN** the user invokes `dobby-worktree create` with PBI ID `123` titled "Add user authentication"
- **THEN** the system SHALL create branch `feat/123-add-user-authentication`, create a git worktree at `<repo-parent>/<repo-name>-worktrees/feat-123-add-user-authentication/`, and report the worktree path to the user

#### Scenario: Create worktree for a Bug
- **WHEN** the user invokes `dobby-worktree create` with a Bug work item ID `456` titled "Login page crash"
- **THEN** the system SHALL create branch `fix/456-login-page-crash` and a corresponding worktree directory

#### Scenario: Create worktree with custom root
- **WHEN** `.dobby/config.json` contains `"worktree": { "enabled": true, "root": "D:\\worktrees" }`
- **THEN** the system SHALL create the worktree under `D:\worktrees\<branch-slug>\` instead of the default sibling location

#### Scenario: Worktree already exists for the PBI
- **WHEN** the user invokes `dobby-worktree create` for a PBI that already has an active worktree
- **THEN** the system SHALL report the existing worktree path and SHALL NOT create a duplicate

#### Scenario: Working tree is dirty in main worktree
- **WHEN** the main worktree has uncommitted changes and `dobby-worktree create` is invoked
- **THEN** the system SHALL proceed normally — worktree creation does not affect the main worktree's state

### Requirement: List active worktrees
The system SHALL list all active git worktrees and identify which ones are associated with PBI/issue branches (by detecting the `feat/<id>-*` or `fix/<id>-*` naming pattern).

#### Scenario: List worktrees with PBI associations
- **WHEN** the user invokes `dobby-worktree list`
- **THEN** the system SHALL run `git worktree list --porcelain`, parse the output, and display each worktree's path, branch, and extracted PBI/issue ID (if the branch matches the naming convention)

#### Scenario: Highlight stale worktrees
- **WHEN** the user invokes `dobby-worktree list` and a worktree's branch has no commits in the last 7 days
- **THEN** the system SHALL mark that worktree as "stale" in the output

### Requirement: Remove worktree
The system SHALL remove a git worktree by PBI ID or branch name, using `git worktree remove` with appropriate cleanup.

#### Scenario: Remove worktree by PBI ID
- **WHEN** the user invokes `dobby-worktree remove` with PBI ID `123`
- **THEN** the system SHALL find the worktree whose branch contains ID `123`, run `git worktree remove <path>`, and confirm removal

#### Scenario: Remove worktree with uncommitted changes
- **WHEN** the user invokes `dobby-worktree remove` and the worktree has uncommitted changes
- **THEN** the system SHALL warn the user and require explicit confirmation before running `git worktree remove --force`

#### Scenario: Worktree cleanup offered on PBI close
- **WHEN** `dobby-close-pbi` successfully closes a PBI and a worktree exists for that PBI
- **THEN** the system SHALL offer to remove the worktree as a post-close cleanup step

### Requirement: Worktree configuration in config.json
The system SHALL support an optional `worktree` block in `.dobby/config.json` with fields `enabled` (boolean, default `false`) and `root` (string, optional custom path).

#### Scenario: Worktrees disabled (default)
- **WHEN** `.dobby/config.json` does not contain a `worktree` block or contains `"worktree": { "enabled": false }`
- **THEN** `dobby-implement-pbi` Phase 1 SHALL use `git checkout -b` as it does today

#### Scenario: Worktrees enabled
- **WHEN** `.dobby/config.json` contains `"worktree": { "enabled": true }`
- **THEN** `dobby-implement-pbi` Phase 1 SHALL delegate to `dobby-worktree create` instead of running `git checkout -b`

### Requirement: Branch creation from base branch
The system SHALL create worktree branches from the repository's default branch (typically `main`), pulling the latest changes before branching.

#### Scenario: Create worktree from up-to-date main
- **WHEN** `dobby-worktree create` runs
- **THEN** the system SHALL run `git fetch origin` and create the worktree with `git worktree add <path> -b <branch> origin/main` to ensure the branch starts from the latest main
