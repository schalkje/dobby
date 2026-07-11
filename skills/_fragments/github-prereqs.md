Run these checks in parallel where possible.

**Check gh CLI**
```bash
gh --version
```
- If `gh` is not found → stop: "GitHub CLI is not installed. Install from https://cli.github.com/"

**Check authentication and show identity**
```bash
gh auth status
```
- If this reports "not logged in" → stop: "Run: `gh auth login`"
- Display the active GitHub user so the user can confirm it's the right account.
