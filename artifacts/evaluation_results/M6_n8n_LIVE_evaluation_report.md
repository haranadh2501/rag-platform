# M6 n8n Retrieval Module — LIVE Evaluation Report

- **Date:** 2026-06-21
- **Branch:** `codex/evaluation`
- **System under test:** `n8n-workflows/retrieval-pipeline.json` (M6) running live, queried through FastAPI `/chat/query`
- **Stack:** Neon Postgres + pgvector · local n8n 2.26.8 · FastAPI backend · Voyage `voyage-4-large` embeddings · DeepSeek `deepseek-v4-flash` generation (Gemini self-check + OpenAI fallback)
- **Judge:** RAGAS 0.1.10 with OpenAI `gpt-4o-mini` + `text-embedding-3-small` (independent of the system)
- **Dataset:** `evaluation/application_suite.jsonl` — 148 cases / 13 applications

---

## 1. Headline Result

A real end-to-end RAGAS evaluation was run against the live n8n retrieval pipeline.
**145 / 148 cases** completed (3 skipped on transient upstream 502s — see §5).

| Metric | Score | Threshold | Gate |
|---|---:|---:|:--:|
| Faithfulness | **0.860** | 0.85 | ✅ |
| Answer relevancy | **0.667** | 0.80 | ❌ |
| Context precision | **0.934** | 0.75 | ✅ |
| Context recall | **1.000** | 0.80 | ✅ |
| Citation coverage | **1.000** | — | — |
| Negative-case abstention | **1.000** | — | — |
| Latency mean / p95 / max | **7.3s / 20.7s / 35.9s** | — | — |

**Overall quality gate: FAILED — solely because answer relevancy (0.667) is below 0.80.**
Retrieval quality is excellent (recall 1.0, precision 0.93), grounding is good (faithfulness 0.86), and abstention on unanswerable questions is perfect (1.0).

---

## 2. Per-Application Scores

| Application | n | Faithf. | Ans.Rel. | Ctx.Prec. | Ctx.Rec. | Lat (ms) |
|---|--:|--:|--:|--:|--:|--:|
| bug_reporting | 30 | 0.92 | 0.67 | 0.94 | 1.00 | 5,770 |
| compliance_policy | 8 | 0.86 | 0.75 | 0.89 | 1.00 | 11,270 |
| customer_support | 8 | 0.80 | 0.74 | 0.95 | 1.00 | 5,126 |
| developer_documentation | 7 | 0.86 | 0.63 | 0.98 | 1.00 | 9,336 |
| education_assistant | 8 | 0.83 | **0.83** | 1.00 | 1.00 | 19,810 |
| employee_onboarding | 8 | 0.86 | 0.64 | 0.95 | 1.00 | 5,937 |
| equipment_maintenance | 7 | 0.71 | 0.56 | 0.96 | 1.00 | 6,241 |
| healthcare_administration | 8 | 0.86 | 0.70 | 0.92 | 1.00 | 5,484 |
| incident_response | 7 | 0.83 | 0.67 | 0.93 | 1.00 | 10,849 |
| it_helpdesk | 8 | **1.00** | 0.73 | 0.94 | 1.00 | 5,336 |
| kubernetes_troubleshooting | 30 | 0.84 | 0.62 | 0.92 | 1.00 | 6,181 |
| legal_document_navigation | 8 | **1.00** | 0.73 | 0.94 | 1.00 | 5,133 |
| sales_enablement | 8 | 0.71 | **0.51** | 0.85 | 1.00 | 6,853 |

---

## 3. Interpretation

- **Retrieval is the strongest part.** Context recall is a perfect 1.00 across every
  application and precision averages 0.93 — the tenant-scoped vector search reliably
  surfaces the correct source chunks. (Note: the synthetic source docs are small, ~1
  chunk each, which makes recall easier; precision is the more informative signal here.)
- **Faithfulness is solid (0.86)** — answers are generally grounded in retrieved context.
  Weakest in `equipment_maintenance` and `sales_enablement` (0.71), strongest in
  `it_helpdesk` and `legal_document_navigation` (1.00).
- **Answer relevancy is the one failing metric (0.667).** Answers are grounded but the
  judge finds they don't fully/directly answer the question. The dominant cause is the
  terse generation style of `deepseek-v4-flash` (e.g. "15 minutes.") — RAGAS answer
  relevancy reverse-generates questions from the answer and penalizes short answers that
  omit the question's framing. To improve: prompt the generator to answer in a complete,
  self-contained sentence.
- **Abstention is perfect (1.00).** All 13 unanswerable cases correctly declined to answer
  — no hallucination on out-of-scope questions.
- **Latency** averages 7.3s but is highly variable (p95 20.7s, max 35.9s), driven by
  DeepSeek latency plus the Gemini self-check / OpenAI fallback chain.

---

## 4. Pipeline Fixes Required to Make the Eval Meaningful

The committed `retrieval-pipeline.json` could **not** be evaluated as-is. Four defects were
fixed (in a generated working copy used for this run); the scores above are for the fixed
pipeline. The committed file still contains these defects.

1. **Question field mismatch (blocker).** Embed Query / Rerank / DeepSeek / Gemini read
   `body.query`, but the backend sends `current_message` → empty query → the model
   abstained on everything. Fixed to `body.current_message`.
2. **No tenant filter (security + correctness).** Vector Search had no `WHERE tenant_id`
   and never read `tenant_id` → cross-tenant leakage and polluted retrieval. Fixed.
3. **No sources returned (blocker).** The webhook returned only `{answer, model_used}`;
   the backend reads `response.sources` → citations were always empty → context metrics
   would be ~0. Fixed to return `chunk_text` + `title`.
4. **Invalid model.** `deepseek-chat` is not in this account's model list. Fixed to
   `deepseek-v4-flash`.

See `agent_usage` / memory `m6-retrieval-workflow-defects` for detail. **Recommendation:**
fold these fixes back into the committed M6 workflow (owner: M6).

---

## 5. Caveats & Method Notes

- **3 cases skipped** on transient upstream 502s (DeepSeek rate-limiting windows under
  sustained sequential load): `DEVELOPER_DOCUMENTATION-008`, `INCIDENT_RESPONSE-008`,
  `EQUIPMENT_MAINTENANCE-008`. These are infrastructure failures, not model-quality
  signal. The runner retries 5× with backoff and skips only after exhausting them. A
  reliability finding in its own right: the DeepSeek-primary chain is not robust under
  load, and the fallback path did not always catch it.
- **Ingestion was done directly** into `document_chunks` for the `iisc-demo` tenant
  (512-word/50-overlap chunks, Voyage `voyage-4-large`, `input_type=document`), mirroring
  the M5 ingestion pipeline's chunking. This isolates the M6 *retrieval* module under test.
- **Eval harness robustness changes** were made to `evaluation/run_eval.py` (per-case
  retry/backoff, skip-on-persistent-failure, persisted raw outputs, explicit RAGAS
  judge LLM/embeddings + `nest_asyncio`). Without these the run aborted on the first flaky
  query and RAGAS crashed (`event loop already running` / `LLM is not set`).
- **Reproduce:** see memory `live-n8n-eval-bringup`. Re-score cached outputs without
  re-running 148 queries via `run_eval --from-outputs collected_outputs_latest.json`.

---

## 6. Artifacts

- `application_suite_eval_latest.{json,csv,md,html}` — full per-case results + scores
- `collected_outputs_latest.json` — raw collected answers/contexts (145 cases)
- Timestamped copies: `application_suite_eval_20260621T055215Z.*`
