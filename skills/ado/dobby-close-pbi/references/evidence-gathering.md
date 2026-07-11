# Screenshot Evidence via Playwright (detail)

Supporting detail for step 4f of the main SKILL.md.

## How to recognize the project supports Playwright evidence

- `playwright.config.ts` exists at the repo root
- `tests/e2e/` contains specs that use `_electron.launch(...)` or a similar app launcher
- A reference spec produces PNGs (e.g., an existing screenshots spec)
- A demo / fixture model exists under `tests/e2e/fixtures/` so the spec can run deterministically

## Evidence file naming — each screenshot MUST have a descriptive filename

- Format: `<phase>-NN-<description>.png`
  - `before-01-entity-editor-current-state.png`
  - `after-01-entity-editor-with-highlight.png`
  - `after-02-relation-browser-dialog-open.png`
- The description becomes the header/caption in the ADO evidence comment
- For bug fixes, `before-NN` and `after-NN` should use matching numbers and similar descriptions so the improvement is directly comparable

## Evidence spec pattern

1. Create `tests/e2e/pbi-<id>-evidence.spec.ts` (or `bug-<id>-evidence.spec.ts`) modeled on the project's screenshot spec.
2. Output screenshots to `tests/e2e/evidence/<prefix>-<id>/*.png` (one folder per PBI). **Add `tests/e2e/evidence/` to `.gitignore`** — once uploaded to ADO the images live as work-item attachments, so keeping them in git is duplication.
3. Set `viewport: { width: 1400, height: 900 }` (or the project default).

**Build & run (do this every time before running the spec — a stale build causes cryptic timeouts):**
```bash
npm run build
npx playwright test tests/e2e/<prefix>-<id>-evidence.spec.ts --reporter=list
```

## After evidence comment format

Each image gets its own heading:
```markdown
## 📸 After Evidence

State after implementation.

### <Description from filename>
![After — <description>](<attachment-url>)

### <Description from filename>
![After — <description>](<attachment-url>)
```

Derive the heading from the filename: strip `after-NN-`, replace hyphens with spaces, title-case.
