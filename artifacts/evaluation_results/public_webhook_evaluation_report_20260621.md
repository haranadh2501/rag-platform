# Public Webhook Evaluation Report - 2026-06-21

## Target

- Public n8n endpoint: `https://n8n-production-c637.up.railway.app/webhook/retrieve`
- Checked inactive/unregistered evaluator-style paths:
  - `https://n8n-production-c637.up.railway.app/webhook/retrieve-eval`
  - `https://n8n-production-c637.up.railway.app/webhook/retrieve-upstream`
- Evaluation tenant sent in payload: `22222222-2222-2222-2222-222222222222`

## Methodology

1. Sent a direct manual JSON probe to the public `/webhook/retrieve` endpoint.
2. Checked whether the public deployment exposes source-returning evaluator webhook paths.
3. Ran the repository evaluator against the public webhook for one case.
4. Ran a 3-case public webhook RAGAS smoke test.
5. Ran a clean 3-case public webhook evaluation with `--skip-ragas` and saved the report bundle.
6. Matched the WhatsApp branch call shape by adding `request_id`, `conversation_id`, `current_message`, and `history` to the evaluation payload, then reran a 3-case public smoke test.

## Results

- Public `/webhook/retrieve` is active and returns `200 OK`.
- Public `/webhook/retrieve-eval` returns n8n `404` because the webhook is not registered.
- Public `/webhook/retrieve-upstream` returns n8n `404` because the webhook is not registered.
- Public `/webhook/retrieve` returns an `answer` and `model_used`, but does not return `sources`, `contexts`, or retrieved chunk text.
- The WhatsApp branch calls n8n through `backend/app/services/pipeline_client.py` using `PIPELINE_URL`, not through `n8n_client.retrieve()`.
- The WhatsApp-style evaluation payload also returns answers from the public webhook, but still does not return `sources`.
- Because the public webhook omits contexts, the clean 3-case run has citation coverage `0.0`.
- RAGAS cannot score the public webhook output as a real RAG result because all retrieved-context lists are empty.

## 3-Case Public Smoke Summary

- Cases: `3`
- Answerable cases: `3`
- Citation coverage: `0.0`
- Mean latency: `29808.923 ms`
- p95 latency: `47724.750 ms`
- Max latency: `47724.750 ms`
- RAGAS: skipped for the clean report because the public webhook response lacks contexts.

## 3-Case WhatsApp-Style Public Smoke Summary

- Cases: `3`
- Answerable cases: `3`
- Citation coverage: `0.0`
- Mean latency: `17585.617 ms`
- p95 latency: `19148.150 ms`
- Max latency: `19148.150 ms`
- RAGAS: blocked because the public webhook response still lacks contexts.

## Artifacts

- `artifacts/evaluation_results/application_suite_eval_20260621T062716Z.*`
- `artifacts/evaluation_results/application_suite_eval_20260621T063151Z.*`
- `artifacts/evaluation_results/application_suite_eval_20260621T070907Z.*`
- `artifacts/evaluation_results/application_suite_eval_latest.*` now points to the 3-case public webhook smoke report.

## Conclusion

The public Railway webhook is usable for answer-only smoke testing through both the direct evaluation payload and the WhatsApp-style payload, but it is not sufficient for citation coverage or RAGAS context metrics until the deployed workflow returns the same `sources` payload shape as the latest repo workflow.
