### Progress ledger (durable resume state)

Maintain a ledger file at `.dobby/evidence/<work-item-id>/ledger.md` (gitignored) for the whole run:

- After completing each phase, append one line:
  `Phase <N> (<name>): complete — commits <base7>..<head7>, <one-line result>`
  (use `git log --oneline` to fill the commit range; write `no commits` for phases that don't commit).
- On resume — including after context compaction — **read the ledger and `git log` first and trust them over your own recollection** of what happened earlier in the session.
- The ledger is the source of truth for "which phases are done"; the conversation is not.
