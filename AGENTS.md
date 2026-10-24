# AGENTS.md — READ BEFORE ANY AI CODING AGENT MODIFIES THIS REPOSITORY

You are working on **SynthLab: MSAI-630 Project 4 Synthetic Data Factory**, with a strict October 25, 2026 demo. Read `MASTER_PLAN.md`, `EVALUATION_PLAN.md`, and `README.md` before changes. This is an educational evaluation of fictional customer-service utterances, not private customer data and not a production privacy solution.

## Hard constraints
1. Use existing **Streamlit + Python** app. **Do not rewrite to React, FastAPI, LangChain, or multi-agent infrastructure**, add auth or database unless asked by owning teammate and product lead.
2. Dataset: original PolyAI BANKING77, original official `train/test` boundaries. Test rows **never** appear in generation prompts. Public train seeds = 8/intent in six fixed intents. Retain CC BY 4.0 attribution.
3. Model: prefer `gpt-4o-mini` through `openai` SDK, configured by environment variables. Never commit `.env`, secrets, raw API keys, or logs that may contain keys. Don't assume ChatGPT subscription means API access.
4. Primary experiment: **6 intents × 20 synthetic rows = 120**. Existing evaluator uses real test examples matched 1:1 and test has only 40 rows/intent; do not increase count per category without correcting evaluation protocol and tests.
5. Metrics: fidelity held-out real-vs-synth AUC; diversity exact duplicates and within-intent sentence-embedding cosine spread; structure independent intent accuracy and length/tone checks; generalization nearest-seed similarity + manual review. Distinguish TF-IDF baseline from MiniLM sentence-embedding values. Never invent results; no treating lexical overlap as a certified privacy guarantee.
6. Save reproducible artifacts: CSV, JSON metrics, batch logs, prompt version, model, dataset revision/sample seed, error/failure logs, human audit evidence. Explicitly indicate missing metrics rather than filling placeholders with invented scores.
7. App must start on Railway with `PORT` and bind 0.0.0.0; keep hosted image light. Heavy sentence-transformer inference runs offline, metrics are loaded into app. No reliance on ephemeral runtime files for durability.
8. Do not make synthetic customer utterances look like genuine private banking records. Never collect sensitive data or claim HIPAA/GDPR/bank regulatory compliance.
9. Before PR: run `pytest -q` and app smoke test; document commands, changed files, tests, failure cases. Keep PR small and constrained to assigned ownership.
10. At instructor's Saturday 10 PM code freeze, refuse feature creep; only critical fixes, deployment, documentation, video, slides.

## Stable Python contracts
- `synthlab/dataset.py`: `load_banking77()` -> `(train_df,test_df)`; `prepare_data(...)` -> `(seeds,model_train,test)`.
- Columns for dataset real rows: `text`, `category`.
- Synthetic rows: `text`, `requested_intent`, `requested_tone`, `requested_length`, `generator_model`, `prompt_version`.
- `synthlab/generator.py`: `generate_batch(...)`, `generate_dataset(...)` and batch status/error log. Per call <=6 records.
- `synthlab/evaluation.py`: `evaluate(seeds,model_train,test,synth)` -> `(metrics,diagnostics,matched_real)`.
- `app.py` remains UI, must never silently replace measured metrics with mock scores.
- `results/latest/` is the reproducible experiment directory; keep blind-study answer keys private. File schema changes must be documented and reviewed by model/eval owners.

## Role-specific instructions for coding agents

**Product Lead / Abhay agent:** Write/maintain `MASTER_PLAN.md`, acceptance criteria, README, problem framing and architecture diagram. Open GitHub Issues; coordinate blockers. Do not override evaluator's metric methodology. Review integrated build + demo, not only UI.

**Model Engineer / Amrit agent:** Inspect dataset loading and generator first; validate actual label names and official source. Make deterministic seed selection (`random_state=42`). Harden JSON parsing and bounded retries; log requested/generated/error counts, model, prompt version. Add short integration test with mocked client. Never pass test rows to prompt or cache a fake "successful" generation. Attach a real run CSV via PR.

**Integration Engineer / Geeth agent:** Keep Streamlit app deployable on Railway with existing Dockerfile and DEPLOYMENT.md. Bind `0.0.0.0:$PORT`; secrets via Railway Variables only. Add live small-batch generation, CSV download, precomputed-results loader, failure visualization, and visible source attribution. Limit live API spend/access; show friendly errors. Avoid importing sentence-transformers on Railway startup. Verify incognito deployed URL.

**Evaluation Lead / Rahul agent:** Freeze evaluation before seeing results. Work on class-matched held-out real-vs-synthetic ROC AUC, duplicate rate and within-intent embedding spread, separate real-trained intent classifier + held-out real accuracy, word-length compliance, nearest-seed checks and true failure table. Run MiniLM offline/Colab. Do not conflate lexical TF-IDF threshold .85 with semantic embedding threshold .92. Use `random_state=42`, clear denominators, saved run manifest. If a metric's denominator or validation fails, report unavailable.

**Ethics & Risk Lead / Shreeja agent:** Inspect public dataset license and attribution, audit generated output for copy-like language and identifiers, conduct human blind audit (rater cannot see answer key). Write specific harms and mitigations; state "screening is not privacy certification". Provide limitations, slides, references, and Q&A answers. Do not add made-up ethics statistics or imply real customers' identities were involved.

## PR completion template
- Issue: #NN / owner:
- Files changed and rationale:
- Schema/contracts affected (yes/no):
- Tests run + actual result:
- Example actual outputs, screenshots or logged failures:
- Security/data-separation check:
- Known limitations:
- Reviewer signoff:

**Never silently modify another owner's component.** Create an Issue/PR requesting API contract change and get lead + affected owner approval.