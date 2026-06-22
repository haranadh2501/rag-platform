# codex.md - Codex Working Notes

> Read this alongside `CLAUDE.md`, `PROJECT_SPEC.md`, and the relevant module spec before making code changes.

## Project Context

This repository is the IISc Grounded Agentic RAG Platform: a multi-tenant document ingestion and grounded chat system built around FastAPI, n8n, PostgreSQL/pgvector, and a Next.js frontend.

Codex work in this repository should preserve the main architecture rule: FastAPI stays a thin gateway, while RAG parsing, chunking, embedding, retrieval, and generation remain in n8n workflows.

## Codex Operating Rules

- Start by checking `git status --short --branch` and reading the files relevant to the requested change.
- Do not overwrite or revert user changes unless explicitly asked.
- Keep edits scoped to the requested module and existing project patterns.
- Prefer tests or focused validation when changing executable code.
- Never commit `.env`, secrets, exported tokens, private keys, or credentials.
- Document significant AI-assisted work in `agent_usage/`.

## Evaluation Work Notes

Recent Codex-assisted evaluation work focused on the M10 evaluation harness and public/local RAG assessment artifacts:

- Added and refined multi-application evaluation datasets.
- Improved evaluation reporting outputs across Markdown, JSON, CSV, HTML, and PDF artifacts.
- Ran public webhook and local evaluation passes where credentials and runtime access were available.
- Preserved notes about missing judge credentials when RAGAS scoring could not run.

## Git Notes

- Branches should generally be created from `dev`.
- Use the `codex/` branch prefix for Codex-created branches unless the team requests a different naming convention.
- Push only after the user asks for it.
- Keep commit messages in the project style, for example `feat(evaluation): add benchmark suite`.

## Agent Usage Notes

When recording Codex usage, include:

- Date and owner.
- Prompt or task summary.
- Files or modules affected.
- Validation performed.
- Corrections or manual decisions made after generation.
- Token usage if available; otherwise state that exact counters were not exposed.
