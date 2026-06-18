---
name: frontend-checks
description: >-
  Run typecheck, lint, and build for the Next.js frontend from the repo root.
  Reports pass/fail per command with only the relevant error lines. Use when
  asked to verify, check, or validate the frontend before or after a change.
allowed-tools: >-
  Bash(test:*), Bash(npm --prefix frontend run typecheck:*),
  Bash(npm --prefix frontend run lint:*),
  Bash(npm --prefix frontend run build:*)
---

# frontend-checks

Run the three frontend verification commands from the repo root and report results concisely.

## 1. Pre-flight

```bash
test -f frontend/package.json
```

If this fails: stop and tell the user `frontend/package.json` is missing.

```bash
test -d frontend/node_modules
```

If this fails: stop and tell the user to run `npm install --prefix frontend` first. Do **not** install automatically unless the user explicitly asks.

## 2. Run checks in order

Run each command. Capture stdout + stderr (use `2>&1`).

```
1. npm --prefix frontend run typecheck
2. npm --prefix frontend run lint
3. npm --prefix frontend run build
```

Stop after the first failure only if the failure would make subsequent checks meaningless (e.g. a build failure after a typecheck failure). Otherwise run all three.

## 3. Report format

Report exactly this structure — nothing else:

```
typecheck  ✓ pass  |  ✗ fail
lint       ✓ pass  |  ✗ fail
build      ✓ pass  |  ✗ fail

[If any failures:]
── typecheck errors ──
<top 5 relevant error lines only — file:line: error TS…>

── lint errors ──
<top 5 relevant error lines only>

── build errors ──
<top 5 relevant error lines only>

Proceed: yes | no (fix <command> first)
```

## Hard rules

- Do **not** edit any file.
- Do **not** read spec or source files.
- Do **not** print full command output — only the lines that matter.
- Do **not** summarise unrelated output (Next.js build stats, chunk sizes, etc.).
- A passing `tsc --noEmit` prints nothing; that is a pass.
- `✔ No ESLint warnings or errors` is a lint pass.
