# Ephemeral Retrieval — Efficiency Report

**Module:** Ephemeral session RAG (ingest → retrieve → purge)
**Workflow optimised:** `retrieval-ephemeral.json` (`POST /webhook/retrieve-ephemeral`)
**Method:** measured before/after with a repeatable eval harness (`eval/run_eval.py`)
**Date of run:** 2026-06-23 · **Environment:** live n8n on Railway + Neon Postgres

---

## 1. Objective

Improve the relevance and speed of the ephemeral retrieval flow, and **quantify** the
improvement with a repeatable, objective benchmark (not subjective spot-checks).

## 2. Evaluation method

- **Corpus:** a *fictional* sports rulebook ("Zorball"). Fictional on purpose — the
  language model cannot answer from its training data, so the benchmark measures
  **retrieval + grounding**, not memorisation.
- **Test set:** 14 questions — **10 answerable** (must contain specific facts from the
  document) and **4 unanswerable** (the system must refuse, not hallucinate).
- **Harness:** ingests the document once, queries each case against the live retrieval
  webhook, and scores retrieval hit-rate, answer correctness, refusal accuracy,
  end-to-end latency (p50/p95), and rerank-score distribution.
- **Identical test set** used for the baseline and the optimised run.

## 3. Headline results (before vs after)

| Metric | Baseline | Optimised | Improvement |
|---|---:|---:|---:|
| Retrieval hit-rate | 100% | 100% | — (already perfect) |
| Answer correctness (10 answerable) | 90% | **100%** | **+10 pp** |
| Refusal accuracy (4 unanswerable) | 0% | **100%** | **+100 pp** |
| **Overall correctness (14 cases)** | **64.3%** | **100%** | **+35.7 pp** |
| Latency p50 (median) | 12.6 s | **6.6 s** | **−48%** |
| Latency p95 (worst-case) | 31.7 s | **7.4 s** | **−77%** |
| Rerank relevance score (mean) | 0.34 | **0.66** | reranking now functional |

> One-line summary: **overall answer quality rose from 64% to 100%, while median
> latency was roughly halved and worst-case latency cut by ~4×.**

## 4. Root-cause finding (why the benchmark mattered)

The benchmark exposed a **latent defect that manual testing had missed**: the workflow
parsed the reranker's response under the wrong key (`results` instead of Voyage's
`data`), so **reranking had been silently inactive** — the system was falling back to
raw vector-search order. Manual queries still "looked right" because vector search
happened to surface the relevant chunk for simple questions. Only the measured
benchmark revealed that the rerank scores were not real (mean 0.34, vector-derived).
After the fix, true cross-encoder relevance scores appear (mean 0.66).

## 5. Changes implemented

1. **Reranking fix** — read the reranker output under the correct key; reranking is now
   actually applied. (Relevance scoring became real: 0.34 → 0.66 mean.)
2. **Relevance threshold** — discard chunks below a relevance score of 0.30; if none
   qualify, the system refuses gracefully **without** calling the language model.
3. **Refusal hygiene** — a refusal no longer returns source citations it did not use.
4. **Deterministic follow-up questions** — switched generation to structured JSON
   output so suggested follow-ups are reliably produced.
5. **Observability** — every response now reports `retrieval_time_ms`, the relevance
   threshold used, and per-source rerank/vector scores.

## 6. Where the gains came from

- **Quality (+35.7 pp overall):** functional reranking + the relevance threshold +
  refusal hygiene turned all 4 unanswerable queries from "incorrectly returned stray
  sources" into clean, source-free refusals, and lifted answer correctness to 100%.
- **Latency (−48% median, −77% p95):** unanswerable queries now short-circuit before
  the expensive generation step. In the baseline, refusals were the *slowest* calls
  (25–32 s) because they still ran a full generation; they now complete in ~6 s.

## 7. Reproducibility

```bash
# baseline (run against the current workflow), then optimised:
python3 eval/run_eval.py --label baseline
python3 eval/run_eval.py --label post
# results saved to eval/results/run-<label>-<stamp>.json
```
Raw data for this report:
`eval/results/run-baseline-20260623a.json` and `eval/results/run-post3-20260623c.json`.

## 8. Scope & caveats (for accuracy)

- Benchmark corpus is small (one fictional document, 2 chunks) and single-turn; numbers
  demonstrate the *direction and magnitude* of improvement, not absolute production
  figures. Re-running on larger, real corpora is the next step.
- The reranker scores *topical relevance*, not *answer presence*; the model's grounded
  refusal remains the final safeguard (it was correct on 4/4 unanswerable cases).
- A history-aware query-rewriting step (for multi-turn chats) is designed but not yet
  shipped — it cannot be measured by this single-turn benchmark.

---
*Generated from the ephemeral retrieval eval harness. See `EPHEMERAL_WORKFLOWS.md`
§15–16 for full technical detail and the improvement roadmap.*
