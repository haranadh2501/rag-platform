# Agent Usage — End-to-End Evaluation Session

- **Date:** 2026-06-21 (run stamp `20260621T2029` IST)
- **Branch:** worked from `feat/m14-teams-bot`; artifacts pushed to `codex/evaluation`
- **Tool:** Claude Code (Opus 4.8, 1M context)
- **Scope:** Evaluate the whole solution end-to-end, run RAGAS against the **live** n8n endpoint,
  and produce improvement + test-gap reports.
- *Authored by the assistant as a session record (the interactive `/export` did not emit a file).*

---

## 1. What was prompted

1. Evaluate the entire solution end to end, in four steps: (1) merge `dev` into the evaluation
   branch, (2) run RAGAS against the **live** endpoint `…/webhook/retrieve` (not locally),
   (3) an exhaustive "areas of improvement" report, (4) a report on what else to test + per-feature
   coverage gaps.
2. Provided live API keys (OpenAI judge, DeepSeek, Gemini, Voyage, Neon) for use as needed.
3. Prepare the reports as PDF.
4. Push the artifacts to the evaluation branch; export the session into `agent_usage/` first.
5. Timestamp filenames to the minute (then switch from UTC to local IST) to avoid same-day clashes.
6. Drop `.md` where a `.pdf` has identical content; keep detailed results alongside the summary.

## 2. What the agent produced

- **Direct-to-n8n RAGAS runner** (`scratchpad/run_eval_n8n_endpoint.py`): POSTs all 148 suite cases
  straight to the live webhook with the backend's payload contract, then scores with the pinned
  RAGAS 0.1.10 judge — reusing `evaluation/run_eval` for scoring/reporting. Supports batched
  collection to JSONL + a separate scoring pass.
- **Live result bundle** `n8n_endpoint_eval_20260621T2029.{json,csv,md,html}` (+ `_latest`).
- **Report 3** `END_TO_END_EVALUATION_REPORT_20260621T2029.pdf` — results + prioritized P0–P3 fixes.
- **Report 4** `TEST_COVERAGE_AND_FEATURE_GAPS_20260621T2029.pdf` — per-module gaps + tests to add.
- **PDF converter** `scratchpad/md2pdf.py` (markdown → print-styled HTML → Chrome headless PDF).

## 3. What had to be corrected (debugging the harness/infra)

The live run was hard-won; each of these was found and fixed:

1. **RAGAS event loop** — `evaluate()` spins its own loop; must run *outside* any running asyncio
   loop. Split collection (threads) from scoring.
2. **Wrong venv** — `.venv-eval` has ragas 0.1.10 but modern langchain → import fails. Used
   `.venv-judge` (era-correct stack).
3. **`datasets` dtype crash** on empty-context rows → declared an explicit RAGAS `Features` schema.
4. **Python `getaddrinfo` flakes on the Railway host** (works via `dig`/`host` = `69.46.46.36`).
   Fixed by pinning the host→IP in the runner (TLS SNI still uses the hostname).
5. **Response schema drift** — the endpoint's `sources` changed mid-session
   (`{chunk_text,title}` → `{id,content}`); parser made tolerant of both. First scored run was
   corrupted purely by this parser mismatch and was re-collected + re-scored.
6. **Abstention false-negative** — the harness reported `negative_abstention_rate 0.0` while the
   system actually refused 16/16 unanswerable questions (harness phrase list too narrow).

## 4. Key findings (see the two reports for detail)

- **Live RAGAS:** faithfulness **0.83** (fails the 0.85 gate; weak on kubernetes/incident/support —
  generation adds world knowledge), answer_relevancy 0.95, context_precision 0.98,
  context_recall 0.92, citation coverage 1.0, abstention 16/16. Latency mean **43 s** (too slow).
- **Governance P0:** the grounding fix runs in **production** but lives only on the unmerged branch
  `fix/m6-retrieval-grounding` (`59422f2`); the committed `retrieval-pipeline.json` on
  `dev`/`codex/evaluation` still has the M6 defects (no tenant filter, reads `body.query`).
- **Step 1 (merge):** no-op — `dev` is already fully contained in `codex/evaluation`.

## 5. Notes

- Independent RAGAS judge used the OpenAI key purely for grading (not the system under test).
- `/cost` token accounting was not captured in this file; the heavy spend was the 148-case live
  run (×~43 s each, DeepSeek/Voyage/Gemini/OpenAI on the n8n side) + the RAGAS judge calls.
