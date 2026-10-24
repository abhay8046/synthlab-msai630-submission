# SYNTHLAB — COMPLETE TEAM EXECUTION PLAN
**MSAI-630-M40, Residency Hackathon, Project 4: The Synthetic Data Factory**  
**University of the Cumberlands | October 23–25, 2026 | Team working agreement (proposed)**

## 0. Read this first
This is a **proposal and implementation plan**, not a description of completed results. The course assignment is in `MSAI-630_Residency_Hackathon_Projects.pdf`, pages 3–5. Sunday is a **10-minute presentation and live demo**, then **5 minutes of Q&A**. Required: working demo + backup recording, 10–12-slide PowerPoint, GitHub repo with README/setup/architecture/evaluation set, and one **privately submitted contribution paragraph per student**. The instructor recommends five roles, listed below. The rubric is Technical 25, Evaluation 25, Real-world 15, Ethics 15, Presentation 15, Collaboration 5. The assignment requires four measurements: fidelity, diversity, structure, and generalization, plus a generation pipeline and evaluation dashboard. No invented performance values.

**Our research question:** Can a small, inexpensive LLM generate useful *fictional* banking-service questions, conditioned on desired intent, tone, and length, without merely reproducing seed questions? What do objective and human tests reveal about quality and failure?

**Scope statement:** We are NOT recreating real account records; NOT collecting real personal banking data; NOT providing financial advice; NOT claiming that synthetic data is automatically anonymous. BANKING77 consists of **public labeled utterances**, not a proprietary financial database. We are testing realistic *language*. The business value is supplementing customer-service AI development/testing with public-anchored examples.

**60-second project pitch:** "Companies need diverse examples to test customer-support AI, but private user conversations can be hard to reuse safely. SynthLab takes an openly licensed dataset of labeled banking queries, asks an LLM to generate new fictional examples under specific controls, then challenges those examples with four independent checks: can we tell fake from real, are they diverse, did they follow the requested category, and are they copying their seeds? We publish failures as well as successes."

## 1. Decisions that prevent scope creep

| Layer | Committed MVP choice | Scope rule |
|---|---|---|
| Data | PolyAI BANKING77, original train/test CSV from the PolyAI GitHub repository, English-only, CC BY 4.0 | Preserve attribution and the official split; test rows are NEVER used in LLM prompts. |
| Domain | Six existing intents: `card_not_working`, `cash_withdrawal_charge`, `pending_transfer`, `card_arrival`, `compromised_card`, `declined_card_payment` | No extra intents until Saturday evening. |
| Dataset sizes | 8 randomly sampled training seeds per intent (48 total); **20 synthetic records per intent = 120 planned**; keep held-out 40 original test questions/intent available | Do not attempt 500 in the existing evaluator: its comparison routine requires at least as many held-out real examples **per intent** as generated examples. |
| Model | Primary **OpenAI `gpt-4o-mini`** via Chat Completions, existing starter OpenAI SDK; `OPENAI_MODEL=gpt-4o-mini` | Keep `gemini-2.5-flash-lite` as optional fallback using Google's OpenAI compatibility endpoint **only after a JSON smoke test**. One primary model is enough. |
| Structured output | JSON with `records:[{text:string}]`; validate schema + word count + allowed attributes after generation | Starter currently uses JSON object mode, not schema-enforced Structured Outputs. Upgrade if straightforward, but never confuse JSON correctness with semantic correctness. |
| App | Streamlit Python | No React/FastAPI rewrite for this deadline. |
| Hosting | Railway service linked to GitHub `main`, one instance, Railway-provided HTTPS domain | Watch RAM on Free tier; never load a heavyweight embedding model at web-app startup. |
| Evaluation | scikit-learn TF-IDF/logistic regression baseline; **offline sentence-transformer embedding upgrade** for diversity/copy checks | Run the heavier embedding experiment locally or in Colab, commit metrics artifact, show from app. |
| Persistence | MVP uses precomputed results committed as CSV/JSON and in-session Streamlit downloads | Supabase is **optional** only for saved run history; don't let DB delay the demo. |
| Work management | GitHub repo, Issues, Projects board, five feature branches/PR owners, required review | No direct push to `main` except initial bootstrap/emergency hotfix agreed by lead. |

**Why these choices (current public documentation):** BANKING77 = 13,083 examples/77 intent labels, 10,003 train and 3,080 test, CC BY 4.0. OpenAI's `gpt-4o-mini` lists $0.15/M input and $0.60/M output tokens; Gemini 2.5 Flash-Lite lists $0.10/M input and $0.40/M output paid-tier tokens, with a conditional free tier; check quota in your own account. Railway Free lists up to 0.5 GB RAM for a deployed service; Hobby has a $5 monthly minimum including usage credit. Supabase Free has 500 MB DB and 1 GB Storage. Costs, model names, available tiers may change; review source links below before enabling billing.

## 2. Exact data lineage and legal attribution

**Canonical source:** https://github.com/PolyAI-LDN/task-specific-datasets/tree/master/banking_data  
**Dataset card/license:** https://huggingface.co/datasets/PolyAI/banking77  
**Direct raw CSV files used by the existing code:**
- Train: https://raw.githubusercontent.com/PolyAI-LDN/task-specific-datasets/master/banking_data/train.csv
- Test: https://raw.githubusercontent.com/PolyAI-LDN/task-specific-datasets/master/banking_data/test.csv

Use the dataset's `text` and `category` fields as provided in the raw CSV. Save source URL + retrieval date and, if possible, the source Git revision/hash so data can be reproduced. Verify all six chosen labels exist before starting. Precompute a small CSV snapshot for the live demo in case external downloads fail. Attribute: "BANKING77, PolyAI; Casanueva et al. (2020), *Efficient Intent Detection with Dual Sentence Encoders*; data licensed CC BY 4.0." License requires attribution, not just a link. Citation paper: https://arxiv.org/abs/2003.04807

**Split hygiene** (owner: data/model and evaluator):
1. Load original `train.csv` and `test.csv`. Filter both to the six fixed intents.
2. Set evaluation RNG seed to **42** and pick **8 train examples per intent** as generation seeds. Never show official test data to generation prompts.
3. Exclude those 48 seed examples from the **real-only intent classifier's** training data (to make control checks less circular). Use the remaining real training rows for that classifier.
4. Generate **20 synthetic records per intent**, ideally distributed across tone and length controls. Include metadata: requested intent, requested tone, requested length, generator model, seed/prompt version and timestamp.
5. Keep official test rows untouched for the intent classifier's held-out accuracy, matched real-vs-synthetic comparison, and human "spot the fake" samples. When training the real-vs-synthetic discriminator, make its *own* train/test split without leakage; do not treat real data used for discriminator fitting as its final score.
6. Compute and export `outputs/synthetic_queries.csv`, `outputs/batch_log.csv`, `outputs/metrics.json`, and `outputs/failure_rows.csv`. Keep a `outputs/run_manifest.json` showing code commit, seed, model, parameters, run time, counts and protocol version.

## 3. Architecture and app workflow

```text
                      PUBLIC PolyAI BANKING77
                        train.csv / test.csv
                                |
                     Filter fixed 6 intents
                                |
                 Train split: 8 examples / intent
                                |
               controlled prompt (intent/tone/length)
                                |
                     OPENAI gpt-4o-mini API
                                |
              JSON parse -> validate -> batch log
                                |
                   SYNTHETIC RECORDS (CSV)
                                |
             +------------------+------------------+
             |                                     |
    Python EVALUATION (offline)          STREAMLIT ON RAILWAY
      1 Fidelity (AUC)                   Generate 4–8 demo rows
      2 Diversity (embeddings)           Preview/download CSV
      3 Structure (intent/length)        Precomputed metric views
      4 Generalization (NN copy)         Failures + spot-the-fake
      5 Blind human audit                Source / ethics / methods
             |
      metrics.json + failure_rows.csv -> committed demo artifacts
```

**UI tabs (for Sunday):** (1) Overview/source, (2) Generate (category/tone/length/count, 4–8 records per live batch, cap output and handle 429/API errors), (3) Data Explorer/CSV, (4) Evaluation Dashboard (four metrics, plots and explanations), (5) Failure Explorer (near-copy / off-intent / length failures), (6) Ethics and Methods + spot-the-fake. Avoid making claims about "privacy-safe"; say "screened for copying risk".

**Output object contract** (everyone and every agent should use this schema):

```json
{
  "text":"My new card still has not arrived and I need it before a trip.",
  "requested_intent":"card_arrival",
  "requested_tone":"polite",
  "requested_length":"short",
  "generator_model":"gpt-4o-mini"
}
```

**API code boundary:** `synthlab/dataset.py` delivers `(train_df,test_df)` and `(seeds,model_train,test)`; `synthlab/generator.py` exposes `generate_batch`/`generate_dataset` and logs errors without suppressing them; `synthlab/evaluation.py` exposes `evaluate(seeds,model_train,test,synth)->(metrics,diagnostics,matched_real)`; `app.py` calls all interfaces without redefining metrics. All changes to columns/schema require agreement in a GitHub Issue first.

## 4. Generation specification and reliability

Prompt specification per batch:
- Task: Write new fictional English banking support questions, not bank account data.
- Intent: one of the six fixed labels; add a plain-English definition.
- Control inputs: tone `neutral|polite|frustrated`; length `short=8–20 words` or `detailed=25–55 words`; requested count 4 or 8 per call.
- Include 3–5 training seed examples from the same intent as topic hints, *never* official test examples.
- Explicitly disallow copying, paraphrasing too closely, identifiers, or real personal details.
- Require JSON object containing only `records` list, and validate the result. Log partial batches, failures, retries, rate limiting and response counts.
- Recommended starter temperature **0.95**, document any later change. Record model alias and, if possible, resolved API model version.
- Do not generate 120 records in one single API response; use batches of four, retry errors with bounded exponential backoff and a maximum retry count. Save progress after every successful batch to avoid losing a run.

**Prompt skeleton (Model Engineer owns implementation):**

```text
You generate completely fictional customer-support questions for academic testing.
Intent: {intent} ({intent_definition})
Tone: {tone}; length: {length_band} ({min_words}-{max_words} words)
Use these publicly licensed example questions only to understand the topic:
{up_to_five_training_seeds}
Write {count} genuinely distinct messages that express the target intent.
Never copy an example. No names, emails, phone numbers, account numbers,
addresses, real transaction IDs, or real personal data. Keep natural English.
Return JSON: {"records":[{"text":"..."}]}. No explanations.
```

**Suggested account configuration (first 30 minutes):** Sign up for or choose an existing API provider; confirm available model, sufficient spend quota, a successful 1-record call, and a 4-record JSON call before writing more code. Provider API billing is separate from a ChatGPT subscription. A stable confirmed model is better than a newer model with untested behavior. **If using Gemini through the existing OpenAI SDK:** Google documents an OpenAI-compatible Chat Completions endpoint (`https://generativelanguage.googleapis.com/v1beta/openai/`), but compatibility with the starter's particular JSON-mode call must be smoke-tested rather than assumed. Do not rewrite the generator merely to chase lower model prices.

## 5. Prespecified EVALUATION PROTOCOL — 25 rubric points

**A. Fidelity: can a classifier tell real from synthetic?** Compare each generated category against the *same category* of held-out real test questions, balanced 1:1. Train a TF-IDF + logistic regression discriminator with a stratified train/test split. Report held-out ROC AUC, sample size, and (optionally) accuracy. AUC close to 0.5 means this discriminator had difficulty; ~1 means easier detection. AUC close to 0.5 on a small sample does NOT prove privacy, usefulness, indistinguishability, or high fidelity. Inspect length and obvious model-writing artifacts that might reveal shortcuts.

**B. Diversity: are examples varied?** Report exact-duplicate rate and mean within-intent **sentence embedding** cosine distance (`1 - cosine_similarity`) using `sentence-transformers/all-MiniLM-L6-v2`. Compare category-matched synthetic vs real distributions. Compute pairwise spread **within intents**, not across unrelated categories; show examples of high- and low-similarity pairs. The current starter evaluates TF-IDF spread, a valid cheap lexical baseline, but owner should add **semantic embedding spread offline** for stronger assignment alignment; record which metric was used. Wide semantic spread alone can signal off-topic nonsense, so cross-reference Structure results.

**C. Structure: did controlled attributes work?** (i) Intent: train a separate intent classifier on the unseeded original train data and validate its real held-out test accuracy before using it as an imperfect label checker on synthetic rows; report synthetic predicted-vs-requested intent match. (ii) Length: count words and report fraction within the selected 8–20 or 25–55 ranges. (iii) Tone: blind-human scoring with explicit rubric, e.g. `neutral|polite|frustrated`, then show agreement and pass rate; do NOT label a self-evaluation by the generator as objective ground truth. (iv) Schema: log valid parsed records / requested records; count API errors separately.

**D. Generalization: are generated rows near-copies?** For each generated row, compute nearest-neighbor similarity to its 8 seed examples (and, optionally, the full original training set) with the same MiniLM embedding model. Report max similarity, mean, count flagged above a predeclared **review heuristic** (e.g. cosine ≥0.90), exact copies and anonymized examples. **Thresholds flag human inspection; they do not certify privacy**. Current starter implements a TF-IDF seed nearest-neighbor ≥0.85 screen; record it as a separate baseline if retained—do not silently equate the two thresholds.

**E. Independent human audit** (strongly recommended): Prepare 20 held-out real and 20 generated queries, balanced by category. Randomize them into an unlabeled file; ask **two independent raters** for `real|synthetic`, naturalness score 1–5, and perceived tone. Keep the answer key private until scoring. Report response count, accuracy, disagreement and representative examples. The starter has `create_blind_audit.py` and `score_blind_audit.py`; do not expose the answer key to raters. A one-question stage trick is a demo moment, **not** research evidence.

**Experimental hygiene:** Pre-register these metric definitions and thresholds before inspecting outputs. Use the official dataset's train/test boundaries; set random seed 42 in data/evaluation; save generator model, temperature and prompts, run manifests and raw CSV. Use graphs with denominators. Include error types, not just happy-path mean. Include one genuine failure or clearly say "none observed in this sample". Don't fabricate results.

**Suggested SUCCESS criteria are internal engineering targets, not course requirements or measured claims:** >=95% valid parse, >=80% length adherence, >=80% intent match **if independent classifier held-out accuracy supports the proxy**, <5% exact duplicates. Report misses honestly, and prioritize tests over reaching an arbitrary threshold.

**Stretch goal only if MVP done:** train a 6-way intent classifier on synthetic samples ONLY and evaluate it on the original real test set, compare it against a same-model classifier trained on a size-matched subset of real training data; report per-class metrics and performance gap, not just one number.

## 6. OWNERS — proposed five-person team charter

> Names below come from your previously shared MSAI group roster. **Confirm that these are the five members for this residency project and adjust ownership as needed.** One person owns each area; everyone reviews the demo.

| Person | Official assignment role | Primary ownership | Required handoff artifact |
|---|---|---|---|
| **Abhay Sunil Dere** | **Product Lead** | Scope, architecture, GitHub project and board, integration milestones, results story, QA/go-no-go | `docs/problem_statement.md`, roadmap/issues, architecture diagram, finished pitch, final acceptance |
| **Amrit Raj Sagar** | **Model/Prompt Engineer** | Public dataset loading coordination, controlled prompting, OpenAI calls, JSON validation, logging and model configuration | `synthlab/generator.py`, `outputs/synthetic_queries.csv`, prompt/model manifest, 3 genuine generation failures or documented none |
| **Geeth Apuroop Kocherla** | **Integration Engineer** | Streamlit UI, app polish, Railway deployment, app secrets, error and CSV flow | `app.py`, `Dockerfile`/Railway settings, HTTPS live URL, deployed smoke test, backup recording support |
| **Rahul Motha** | **Evaluation Lead** | Four checks, benchmark preparation, held-out data hygiene, charts, blind human audit, uncertainty | `synthlab/evaluation.py`, `outputs/metrics.json`, `outputs/failure_rows.csv`, evaluation methods and plots |
| **Shreeja Kanneganti** | **Ethics & Risk Lead** | Licence/attribution, privacy/identifiers, bias/limitations, manual audit, ethics slide, README and slide coordination | `docs/ethics_risks.md`, audit records, references, 10–12 slides collated, Q&A risk sheet |

**Pairing:** Abhay reviews integration and deploy with Geeth; Rahul checks model data contract with Amrit; Shreeja independently inspects failure samples and conducts human audit with a rater who did not see answer key. Slide content supplied by every owner; Shreeja coordinates assembly but does not invent their results. Individual private statements are each person's responsibility.

**Decision authority:** Abhay is scope/schedule integrator; Rahul owns definitions of metrics so they are not altered to boost results; Amrit owns generator prompt version; Geeth owns deployed runtime/security; Shreeja owns risk language and attribution. Breaking schema changes need shared PR review. If a task is blocked >30 min, file issue with blocker and ask for pair help instead of switching frameworks.

## 7. Exact proposed Friday–Sunday timeline (internal targets)

### Friday, Oct 23 (kickoff evening; start now)
- **T+0–30 min:** Abhay creates GitHub repo/project board, invites teammates, posts fixed scope + this plan; all accept one primary role. Amrit verifies dataset download/model API with 4-record test. Geeth verifies local Streamlit launch. Rahul freezes metric definitions. Shreeja confirms source license and risk framing.
- **By Friday 10 PM ET (team target, not instructor deadline):** `main` has working local happy-path on at least 1 intent, first saved synthetic rows, and a Railway placeholder/initial deployment. Open PRs and smoke tests visible. Everybody has a GitHub issue.

### Saturday, Oct 24
- **By 12 PM ET:** Course checkpoint 1 — full end-to-end skeleton 6 intents supported, API generations working, CSV preview, evaluation invoked successfully, Railway URL loads. Mock/demo artifacts are explicitly labeled if not genuine yet.
- **12 PM–4 PM:** Amrit generates 120 records (6×20) and freezes result CSV/prompt manifest. Rahul runs discriminative fidelity, diversity, structure and nearest-neighbor check; logs evaluator failures. Shreeja organizes independent blind audit. Geeth adds metric/failure visualization.
- **By 6 PM:** Real metrics/plots and failure examples merged. Human audit scoring completed if practical. Abhay checks story, data leakage risk and model costs; Shreeja drafts ethics and citation slides.
- **By ~10 PM:** Instructor's Saturday code freeze: stable main, recorded backup demo, README setup/architecture/evaluation description, 10–12 slides with ACTUAL figures, rehearsed demonstration. **No feature work after freeze.**

### Sunday, Oct 25 (morning)
- Open deployed URL before session, test the API and precomputed dashboard, confirm video file plays offline, rehearse exact click path. Present **10 min**, then **5 min Q&A**. All five submit their **own private individual contribution paragraph** to instructor; final GitHub repo and PowerPoint available.

**CUT ORDER if behind:** cut user login → cut Supabase → cut fancy charts → cut automatic live full evaluation → reduce to 4–6 fixed intents → keep core generation + four honest metrics + failures + demo + slides. Do not cut evaluation or attribution. Work offline if API fails and show precomputed genuine run results with disclosure.

## 8. GitHub workflow and ready-made issue backlog

1. Create one repository `synthlab-msai630-project4`. Add five team collaborators. Create one GitHub Project titled `SynthLab | Oct 23–25` and attach each Issue.
2. Board columns **Backlog → Ready → In Progress → In Review → Done → Blocked**. Labels `data`, `model`, `frontend`, `evaluation`, `deploy`, `ethics`, `slides`, `p0`, `p1`, `blocker`.
3. Each Issue has: objective, owner, deadline, input contract, acceptance criteria and supporting proof (screenshot/CSV/CI). Copy entries from `GITHUB_ISSUES.md`.
4. Branches `feat/generator`, `feat/dashboard`, `feat/evaluation`, `docs/ethics`, `docs/pitch`, etc. Commit focused changes. PRs refer to an Issue with `Closes #NN`. Do a peer review even if brief. CI must pass before merging.
5. Agree code/data contracts in this document; do not overwrite teammates' files. No credentials in git. Use `.env` locally and Railway service variables. If a PR changes the schema it must update tests and be approved by generator/evaluation owners.
6. Branch protection (if enabled/available): require PR and green tests on `main`; maintain one integrator. At Saturday code freeze switch main to demo-only hotfix approvals.
7. Project management should reflect actual contribution: each owner moves Issues, posts PR links and adds evidence by end of Saturday. GitHub Projects can render board/table from Issues and PRs.

## 9. Railway shipping instructions (Integration Engineer)

**Before deploy:** Verify starter locally: `python -m venv .venv`, activate environment, `pip install -r requirements.txt`, create local `.env`, add `OPENAI_API_KEY`, set `OPENAI_MODEL=gpt-4o-mini`, run `python -m pytest -q`, launch `streamlit run app.py`. Note: a ChatGPT Plus/Pro subscription **does not itself provide** API billing credits. Obtain key/allowance separately. If errors, log redacted stack trace without keys.

**Deploy:** Link the GitHub `main` branch in Railway → New Project / Deploy from GitHub repo → service variables `OPENAI_API_KEY`, `OPENAI_MODEL=gpt-4o-mini`, optionally `APP_DEMO_PASSWORD` if implemented. A Dockerfile is included with a shell-form Streamlit command that binds to `0.0.0.0` and Railway's dynamic `$PORT`. Generate a public `*.railway.app` domain in Service Settings → Networking. Test URL from an incognito window, check Railway logs for startup failures and verify no secret appears in logs. The service redeploys on main-branch pushes if GitHub autodeploy is enabled.

**Critical host limitation:** Railway Free may offer only **0.5 GB RAM** per service; CPU/PyTorch-based sentence embedding models may exceed available memory. Do heavy MiniLM/scikit-learn evaluation locally or on Colab first and publish the real `metrics.json`/CSV artifacts in repo for display. Live generation of 4–8 rows can use the hosted API. Runtime-created local files may disappear on redeploy; do not rely on Railway's ephemeral filesystem to preserve 120-record runs.

**Public API risk:** A public Generate button could let strangers spend your API credits. Protect with simple demo passcode or disable live generation outside the session; hard-limit batch size and rate, track usage; hide the key strictly server-side in Railway variables. Streamlit isn't a full auth service. Back up video and charts should work even when provider API is down.

**Source docs:** https://docs.railway.com/deployments/github-autodeploys ; https://docs.railway.com/deployments/start-command ; https://docs.railway.com/networking/public-networking ; https://docs.railway.com/variables ; https://docs.streamlit.io/deploy/tutorials/docker

## 10. Supabase is optional (do not build by default)

**Add only if necessary:** You need durable multi-user run history after redeploy, want to share generation sessions, or want persistent raw CSV across deployments. For Sunday the precomputed files and downloads suffice. If adding, one narrow table is enough:

```sql
create table public.generation_runs (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  model text not null,
  prompt_version text not null,
  parameters jsonb not null,
  synthetic_records jsonb not null,
  metrics jsonb,
  status text not null default 'completed'
);
alter table public.generation_runs enable row level security;
-- NO public policies for the weekend MVP. Access only from the server
-- using a protected secret key, never from the client/browser.
```

For a demo with no browser-based authenticated users, do not grant anonymous read/write access and never expose Supabase secret/service-role key. Service-side DB persistence must be intentionally implemented; creating the table alone does not change the starter's behavior. Verify insert/read with a fake fixture and inspect RLS before announcing persistence. Free projects can pause with inactivity; do not rely on a dormant DB for a critical demo. **Skip Supabase entirely if the Saturday midday checkpoint is at risk.**

**Supabase sources:** https://supabase.com/docs/guides/platform/billing-on-supabase ; https://supabase.com/docs/guides/database/postgres/row-level-security ; https://supabase.com/docs/guides/platform/free-project-pausing

## 11. Security, ethics, evaluation limitations

| Risk | Specific control | Honest limitation |
|---|---|---|
| Copying source utterances | Nearest-neighbor search against seeds and original training questions; manual inspection; cite source | Similarity threshold is NOT differential privacy or anonymity guarantee. |
| Financial information exposure | Do not accept real customer uploads, personal names, account identifiers or transaction IDs; use publicly licensed utterances and fictional output | Regex screening is imperfect, not sensitive-data removal certification. |
| Intent/sentiment bias | Six fixed categories, category-balanced evaluation; report English-only domain | Doesn't represent real bank users, languages or demographics. |
| Model output quality | Controlled intent/tone/length, JSON validation, classifier + human audit | Classifier errors can mislabel generated rows; show real holdout accuracy. |
| API compromise/cost | Secrets in Railway, rate limit/public-demo protection, budgets, no logs of keys | This is an academic prototype, not bank-ready. |
| Experiment cherry-picking | Precommitted metrics, raw run logs, failures and limitations; no fabricated data | 120 records and two human raters have substantial uncertainty. |
| Misleading "fake = safe" message | Explicit risk slide, attribution, avoid production-readiness promise | Public dataset isn't a proxy for private medical/finance data. |

## 12. Required slide plan (11 slides) and 10-minute script

| Slide | Owner | Message / evidence | Time (target) |
|---|---|---|---|
| 1. Title + pitch | Abhay | SynthLab one-sentence research question | 0:30 |
| 2. The user/problem | Abhay | Teams lack varied labeled test utterances; privacy motivation stated cautiously | 0:55 |
| 3. Source and dataset | Amrit | BANKING77 77 intents; selected 6; train/test counts + CC BY attribution | 0:55 |
| 4. Architecture | Geeth | Flow from source to LLM to evaluator to Streamlit/Railway | 0:55 |
| 5. Generation controls | Amrit | Intent, tone, length, JSON and actual generated example | 0:55 |
| 6. Live app demo | Geeth | Run small generation or replay short prepared result, inspect download | 1:50 |
| 7. Fidelity + diversity | Rahul | Actual ROC AUC, n, embedding spread vs real, duplicate rate | 1:05 |
| 8. Structure + generalization | Rahul | Intent/length/tone adherence, copy similarity / flagged examples | 1:05 |
| 9. Failure analysis | Rahul + Amrit | 1–2 real failure cases and mechanism | 0:55 |
| 10. Ethics/risks | Shreeja | Leakage, biased coverage, classifier limits, mitigation/non-guarantees | 0:55 |
| 11. Takeaways + roadmap | Abhay | What data helps; what fails; synthetic-to-real stretch; team contribution | 0:55 |

**Total target ≈10 min**, rehearse with a timer and reduce if needed. Live audience "spot the fake" can be incorporated into Slide 6 or 9 only if the timing allows. Q&A preparation: "Does realistic mean private?" (no), "How independent is evaluation?" (classifiers held out + human audit), "Does AUC 0.5 prove fidelity?" (no), "Why six intents?" (controlled experiment within 40 hours), "Why no database?" (stateless reproducible output sufficient for MVP).

## 13. Acceptance checklist / Sunday definition of done

- [ ] All five owners named and have GitHub Issues/PRs.
- [ ] Stable Railway HTTPS URL opens from incognito; basic run and recorded backup work.
- [ ] Source attribution, license, original data splits and prompt-seed selection documented.
- [ ] Successful generation of actual synthetic data (target 120; disclose actual if fewer).
- [ ] Four required evaluation categories presented with actual values, methods, denominators and uncertainties.
- [ ] At least one checked failure/limitation shown honestly; no altered thresholds post hoc.
- [ ] Generated downloadable CSV and independent metrics/results artifacts kept for reproducibility.
- [ ] 10–12 slides and rehearsal performed; 10-minute cap respected.
- [ ] GitHub README includes local setup, architecture diagram, evaluation set and instructions; no keys in git.
- [ ] Individual privately submitted contribution statements prepared by each student.

## 14. Verified public references (checked Oct 23, 2026)

1. **Course source** — `MSAI-630_Residency_Hackathon_Projects.pdf`, pp. 3–5, instructor's rubric/deadlines.
2. PolyAI, **BANKING77** dataset and CC BY 4.0: https://huggingface.co/datasets/PolyAI/banking77
3. Casanueva, I., et al. (2020). **Efficient Intent Detection with Dual Sentence Encoders**: https://arxiv.org/abs/2003.04807
4. OpenAI, **GPT-4o Mini model and token rates**: https://developers.openai.com/api/docs/models/gpt-4o-mini
5. Google, **Gemini pricing**: https://ai.google.dev/gemini-api/docs/pricing
6. Google, **OpenAI compatibility**: https://ai.google.dev/gemini-api/docs/openai
7. Google, **Rate limits vary by account**: https://ai.google.dev/gemini-api/docs/rate-limits
8. Sentence Transformers, **semantic similarity / MiniLM examples**: https://sbert.net/docs/sentence_transformer/usage/semantic_textual_similarity.html
9. Railway, **Pricing and resource caps**: https://docs.railway.com/pricing/plans
10. Railway, **GitHub auto deploy**: https://docs.railway.com/deployments/github-autodeploys
11. Railway, **Start commands**: https://docs.railway.com/deployments/start-command
12. Supabase, **Billing Free limits**: https://supabase.com/docs/guides/platform/billing-on-supabase
13. Supabase, **Row Level Security**: https://supabase.com/docs/guides/database/postgres/row-level-security
14. GitHub Docs, **Projects quickstart**: https://docs.github.com/en/issues/planning-and-tracking-with-projects/learning-about-projects/quickstart-for-projects
15. Streamlit Docs, **Docker deployment**: https://docs.streamlit.io/deploy/tutorials/docker

**Final principle:** Show what the model actually generated, how the evaluations were defined before observing the outputs, and where it failed. That is stronger than an impressive-looking dashboard with unreliable numbers.