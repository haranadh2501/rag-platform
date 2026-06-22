# Yasha Codex Token Usage Record

Date: 2026-06-20
Workspace: `C:\Users\yasha\Desktop\Mtech\DL\course_project\rag-platform`
Thread branch: `codex/evaluation`

## Token Usage

Exact token counts are not available from the tools exposed in this Codex desktop session.

I checked the available goal/session accounting tool during this thread. It returned:

```json
{
  "goal": null,
  "remainingTokens": null,
  "completionBudgetReport": null
}
```

Because no token accounting was exposed, this file does not invent or estimate token totals.

## Recorded Usage So Far

- Created and maintained `evaluation/codex_conversation_log.md` at the user's request.
- Fetched the latest `origin/dev`.
- Merged `origin/dev` into `codex/evaluation`.
- Ran evaluation preflight with `python -m evaluation.run_test_suite`.
- Generated timestamped evaluation preflight reports in `artifacts/evaluation_results/`.
- Checked readiness for full live evaluation against n8n-backed RAG.
- Verified local backend and n8n were not reachable.
- Verified Docker Desktop/daemon was unavailable from this session.
- Verified the documented Railway backend was reachable but running with `mock_n8n: true`.
- Created this token usage record under `agent_usage/yasha_token_usage/`.
- Attempted live smoke evaluation with `python -m evaluation.run_eval --suite-dataset --skip-ragas --max-cases 3`.
- The smoke evaluation failed with `httpx.ConnectError: All connection attempts failed` because the backend at `http://localhost:8000` was unreachable.
- Rechecked local backend and n8n; both were unreachable.
- Did not run full scored evaluation because the live smoke test failed.
- Updated `specs/MODULE_SPEC_M10.md` with the current evaluation suite, live smoke/full evaluation commands, live prerequisites, and n8n setup references.
- Confirmed n8n setup documentation exists in `docs/LOCAL_SETUP.md`, `docs/DEPLOYMENT.md`, `docs/CREDENTIALS_README.md`, and specs M5/M6/M11.
- Set up local Docker services for Postgres, n8n, and backend.
- Created local ignored `.env` with `MOCK_N8N=false` and placeholder/blank provider keys.
- Imported and activated n8n workflows after patching workflow exports for local n8n import compatibility.
- Ran migrations and seeded the local admin user.
- Verified backend health and admin login.
- Ran evaluator smoke and full live collection before wiring `PIPELINE_URL`; those runs completed but were invalid quality evidence because they used the mock pipeline response.
- Patched evaluator mock detection to catch mock pipeline responses.
- Wired backend `PIPELINE_URL` to n8n and added `query` to the pipeline payload.
- Re-ran one-case live smoke against real n8n; it failed with `502` because n8n `/webhook/retrieve` returned an empty response body.
- Added direct Railway n8n evaluation mode to the evaluator.
- Added `--n8n-url`, `--n8n-token`, `--n8n-tenant-id`, and `--max-chunks-per-query` evaluator options.
- Updated evaluation docs and the M10 spec with the direct n8n test path.
- Ran `python -m unittest tests.test_evaluation_dataset`; all 12 tests passed.
- Tested local n8n at `http://localhost:5678`; health returned `200`.
- Posted to local `http://localhost:5678/webhook/retrieve`; it returned `200 OK` with an empty body.
- Ran direct local n8n evaluator smoke; it failed on `K8S-EVAL-001` because n8n returned a non-JSON empty response.
- Exported the active local retrieval workflow and confirmed it is published but structurally incomplete for real RAG output.
- Inspected Shreya's fetched M6 retrieval workflow and confirmed it has a fuller retrieval chain but uses an Execute Workflow Trigger plus n8n credentials, not a public webhook.
- Generated and imported a temporary local `M6 Retrieval Pipeline v2 Public Webhook` workflow using path `retrieve-v2`.
- Published the imported `retrieve-v2` workflow and restarted local n8n.
- Verified `retrieve-v2` is registered, but it returns `500` because Shreya's imported credential ID for `Voyage API` does not exist locally.
- Checked local `.env`; provider keys are blank while `POSTGRES_PASSWORD` is present.
- Ran evaluator smoke against `http://localhost:5678/webhook/retrieve-v2`; it reached n8n and failed with `500 Internal Server Error`.
- Imported user-supplied provider and Neon credentials into local n8n without writing secret values to repo files.
- Removed temporary credential import files from host and container after import.
- Verified small direct health checks for DeepSeek, Gemini, and OpenAI returned HTTP 200.
- Patched the local n8n workflow's Gemini auth/header style, malformed Gemini URL, and LLM JSON body construction.
- Verified a manual `retrieve-v2` POST returned a model-generated JSON response.
- Ran a 3-case direct n8n smoke; it collected responses but had zero citation coverage and remained unsuitable as quality evidence.
- Found Shreya's imported workflow fans out after vector search, causing repeated model calls and provider batching/rate errors.
- Patched vector search to `LIMIT 1` for smoke testing, but n8n later disconnected/restarted during evaluator probing.
- Created and imported a new local `Stable Retrieval Public Webhook` n8n workflow at `POST /webhook/retrieve-stable`.
- The stable workflow aggregates pgvector results into one context item before model generation, avoiding the fan-out/rate-limit issue in Shreya's imported workflow.
- Confirmed the stable workflow exists, is active, and has `triggerCount: 1`.
- A direct `retrieve-stable` probe disconnected while n8n logs showed database ping and external registry timeout instability.
- Fetched all remote branches from GitHub after the upstream fan-out fix was reported.
- Confirmed `origin/dev` now includes the updated M6 retrieval workflow and `origin/feat/m6-retrieval` is merged into `origin/dev`.
- Confirmed `origin/codex/evaluation` also contains latest `origin/dev`; local `codex/evaluation` is now ahead 1 and behind 20 relative to the remote branch.
- Imported the updated upstream retrieval workflow into local n8n as `Upstream Retrieval Check` at `POST /webhook/retrieve-upstream`.
- Verified the updated workflow no longer fans out downstream: vector search produced 10 items, aggregate reduced to 1, and model/response nodes each ran once.
- Ran one evaluator smoke case against `retrieve-upstream`; collection succeeded and wrote `application_suite_eval_20260620T121831Z.*`, but citation coverage remained `0.0` because the upstream response does not include `sources`.

## Full Evaluation Blockers Observed

- No `.env` file was present in the workspace.
- No `EVAL_*` credentials or `OPENAI_API_KEY` were set in the shell environment.
- Local `http://localhost:8000` was unreachable.
- Local `http://localhost:5678` was unreachable.
- Docker was unavailable.
- The cloud backend at `https://rag-platform-production.up.railway.app/health` reported `mock_n8n: true`.
- The probed Railway n8n URL `https://n8n-production-c637.up.railway.app/webhook/retrieve` returned `404 Not Found`.
- Shreya's fetched M6 retrieval branch uses an Execute Workflow Trigger, not a public webhook endpoint.
- Local n8n `/webhook/retrieve` is active but currently returns an empty body.
- Local n8n `/webhook/retrieve-v2` is active but blocked by missing n8n provider credentials.
- After credential import, `/webhook/retrieve-v2` can reach providers, but the imported workflow still needs structural cleanup before full evaluation.
- Stable workflow `/webhook/retrieve-stable` is the preferred fix path, but local n8n runtime stability still needs cleanup before rerunning full evaluation.
- Updated upstream workflow fixes fan-out, but still needs source/citation response fields for evaluation quality evidence.

## Notes

This record can be extended with exact token usage later if Codex exposes token accounting for the session or if a screenshot/export from the app is added to this folder.

## 2026-06-20 Full Evaluation Work

- Exact Codex token usage for this thread was not exposed by the local goal/usage API during this turn.
- Work performed:
  - patched and tested the n8n retrieval workflow response/query path;
  - imported evaluation corpus into an isolated tenant without storing credential values;
  - ran a 3-case direct n8n smoke evaluation;
  - ran the full 148-case direct n8n evaluation;
  - created `artifacts/evaluation_results/full_evaluation_report_20260620.md`;
  - updated the conversation log.
- Full evaluation artifact set:
  - `artifacts/evaluation_results/application_suite_eval_20260620T125517Z.json`
  - `artifacts/evaluation_results/application_suite_eval_20260620T125517Z.csv`
  - `artifacts/evaluation_results/application_suite_eval_20260620T125517Z.md`
  - `artifacts/evaluation_results/application_suite_eval_20260620T125517Z.html`
- Verification:
  - `python -m json.tool n8n-workflows/retrieval-pipeline.json`
  - `python -m unittest tests.test_evaluation_dataset`

## 2026-06-21 - Batched evaluation/report update

- Work performed: restored direct n8n evaluator behavior, added deterministic batching, added observability reporting, ran unit tests, ran a five-case public webhook smoke test, and prepared consolidated report artifacts.
- Token usage note: exact platform token counters are not exposed in the workspace, so this log records activity-level usage rather than numeric token totals.

## 2026-06-21 - Full public Railway batch evaluation

- Work performed: launched and monitored the 30-batch public Railway evaluation, consolidated 148 case results, generated a PDF report, render-checked the PDF, and scanned artifacts for secret patterns.
- Runtime note: RAGAS was not run in this pass because no judge API key was available in the shell environment.

## 2026-06-22 - RAGAS scoring attempt

- Work performed: ran RAGAS scoring against the completed public Railway evaluation output, investigated null metrics, confirmed the OpenAI judge key returned `insufficient_quota`, generated a PDF attempt report, render-checked the report, and scanned artifacts for secret patterns.
- Token usage note: exact platform token counters are not exposed in the workspace, so this log records activity-level usage rather than numeric token totals.
