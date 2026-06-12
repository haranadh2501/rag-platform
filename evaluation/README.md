# Bug-Reporting RAG Evaluation

This folder contains a deterministic synthetic corpus, 30 evaluation questions,
dataset validation, live API collection, and RAGAS scoring for:

- Faithfulness
- Answer relevancy
- Context precision
- Context recall

The API's Gemini self-check is recorded as `system_faithfulness`. RAGAS
faithfulness is computed separately and must be treated as the evaluation score.

## Dataset

The generated corpus contains:

- Bug triage and severity rules
- Mobile known issues
- API and webhook known issues
- Factoid, procedural, reasoning, multi-hop, safety, and unanswerable questions

Regenerate it:

```powershell
python -m evaluation.generate_bug_dataset
```

Validate structure and verify every reference context exists verbatim in its
declared source document:

```powershell
python -m evaluation.validate_dataset --strict
```

## Prepare the system

1. Ingest all files from `evaluation/sample-data/bug-reporting/` into one
   evaluation tenant.
2. Start the backend with `MOCK_N8N=false`.
3. Set either `EVAL_BEARER_TOKEN`, or `EVAL_EMAIL` and `EVAL_PASSWORD`.
4. Install dependencies:

```powershell
pip install -r backend/requirements.txt
pip install -r evaluation/requirements.txt
```

RAGAS 0.1.10 uses an evaluator LLM and embeddings. Set `OPENAI_API_KEY` for the
independent evaluator. This is separate from the model response and from the
system-provided Gemini faithfulness score.

## Run

Collect responses and run all four RAGAS metrics:

```powershell
$env:EVAL_BASE_URL = "http://localhost:8000"
$env:EVAL_EMAIL = "admin@iisc-demo.com"
$env:EVAL_PASSWORD = "your-password"
$env:OPENAI_API_KEY = "your-evaluator-key"
python -m evaluation.run_eval --strict-dataset
```

Enforce the project quality targets and return a non-zero exit code when any
metric fails:

```powershell
python -m evaluation.run_eval --strict-dataset --enforce-thresholds
```

Default gates are faithfulness `0.85`, answer relevancy `0.80`, context
precision `0.75`, and context recall `0.80`. Each can be overridden with the
corresponding `--min-*` argument.

For a plumbing-only run without RAGAS:

```powershell
python -m evaluation.run_eval --skip-ragas --max-cases 3
```

The runner rejects fixed mock responses unless `--allow-mock` is explicitly
provided. Reports are written to `artifacts/evaluation_results/` as JSON and CSV.

Unanswerable cases are excluded from the four RAGAS averages because context
precision and recall are not meaningful without a reference context. They are
reported separately through `negative_abstention_rate`.
