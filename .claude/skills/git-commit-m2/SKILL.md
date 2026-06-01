---
name: git-commit-m2
description: >-
  Commit the current working-tree changes in this repo with a generated
  Conventional Commit message, after rebasing the branch onto the latest
  remote dev. Use when the user asks to commit changes, "save work to git",
  or "run git-commit-m2". Gathers `git status` + `git diff HEAD` as context,
  syncs with origin/dev (fetch + rebase), generates a `type(scope): summary`
  message describing what changed, and commits. NEVER pushes.
allowed-tools: >-
  Bash(git status:*), Bash(git diff:*), Bash(git add:*), Bash(git commit:*),
  Bash(git log:*), Bash(git rev-parse:*), Bash(git fetch:*), Bash(git rebase:*),
  Bash(git stash:*), Bash(git pull:*)
---

# git-commit-m2

Commit the current changes in this repository with a clear, generated message —
on top of the latest `origin/dev`. **This skill never pushes.** Only `git`
commands are available; no other shell tools.

## 1. Gather dynamic context
Run and read the output before doing anything else:
- `git status` — staged / unstaged / untracked files and the current branch.
- `git diff HEAD` — the actual content changes vs the last commit.
- `git log --oneline -5` — match the repo's existing message style.

## 2. Guard the branch
Run `git rev-parse --abbrev-ref HEAD`. Commit only on a **feature branch**
(e.g. `fix/m2-auth-core`). If you are on `dev` or `main`, **stop** and tell the
user to switch to a feature branch — do not create one silently.

## 3. Sync onto the latest remote dev (before committing)
A rebase needs a clean tree, so set local changes aside first:
1. If `git status` shows any changes, `git stash push -u -m git-commit-m2`.
2. `git fetch origin`
3. `git rebase origin/dev`
4. If you stashed, `git stash pop`.

**Conflict handling:** if either the rebase or the `stash pop` reports
conflicts, **stop immediately** and report the conflicting files to the user.
Do NOT attempt to auto-resolve, and do NOT run `git rebase --abort` /
`git checkout` to discard their work without asking.

## 4. Stage deliberately
From `git status`, `git add` only the files that belong to this change. Never
blindly `git add -A` if unrelated files are present. Never stage secrets
(`.env`), caches, or build artifacts.

## 5. Generate the commit message
Conventional Commits: `type(scope): summary`, where
`type ∈ {feat, fix, test, docs, chore, refactor}`. Base the message on the
**actual diff** — summarize *what changed* in the affected components:
models, schemas, API endpoints, migrations, training loop, config, or tests.
Keep the subject ≤ 72 chars; add a short bullet body when several files changed.

Always end the message with this trailer on its own line:
```
Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
```

## 6. Commit
Use a heredoc so the multi-line message is preserved:
```bash
git commit -m "$(cat <<'EOF'
type(scope): summary

- key change 1
- key change 2

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

## 7. Report
Show the result with `git log --oneline -1` and tell the user the commit is
local only — they push manually when ready.

## Hard rules
- **NEVER run `git push`** — it is not in this skill's allowed tools, and
  pushing is always the user's explicit, manual step.
- Only `git` commands are permitted.
- Stop and ask on any rebase/stash conflict; never discard the user's changes.
