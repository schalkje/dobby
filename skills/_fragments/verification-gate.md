### Verification gate — before any completion claim

Before stating that anything is done (a phase, the implementation, the closure):

1. **Identify** the command that would prove the claim (test run, build, `gh pr view`, work-item state query).
2. **Run it fresh** — do not reuse output from earlier in the session.
3. **Read the full output**, then claim the result citing that output.

Never claim completion with "should", "probably", or "seems to". Work that was not verified is reported as *unverified*, not as done.
