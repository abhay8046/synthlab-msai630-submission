# GITHUB_ISSUES.md — Create these Issues immediately

Create GitHub repository `synthlab-msai630-project4`; create a GitHub Project named `SynthLab | Oct 23–25` in **Board** mode. Status fields: Backlog, Ready, In Progress, In Review, Blocked, Done. Labels: `p0`, `p1`, `data`, `model`, `frontend`, `evaluation`, `deploy`, `ethics`, `slides`. Invite all five collaborators. Create all issues below with assignee and acceptance criteria, then add them to the Project board. Dates are proposed internal commitments, not professor-mandated clock times.

| ID | Issue title | Owner | Target | Acceptance criteria |
|---|---|---|---|---|
| #01 | [P0] Freeze scope, architecture, data contract | Abhay | Fri kickoff | Six intents, 120-row goal, role charter, architecture diagram, explicit API/CSV schema approved. |
| #02 | [P0] Dataset retrieval and train/test isolation | Amrit | Fri evening | Public CSV loads, label names verified, 8 seeds/intent with seed=42, test held out, source/license documented. |
| #03 | [P0] Generate actual JSON records via model API | Amrit | Sat noon | One and four-record call succeed, 6-intent handling, tone+length, output CSV, batch logs and real errors. |
| #04 | [P0] Integrate Streamlit generation and download | Geeth | Sat noon | App loads local, user generates 4–8 rows, preview + CSV download, errors do not crash app. |
| #05 | [P0] Deploy Railway HTTPS app | Geeth | Sat noon | Deploy via main, secrets configured, correct `$PORT`, incognito opens, API live smoke test, no leaked secret. |
| #06 | [P0] Predefine and implement four evaluations | Rahul | Sat noon skeleton; Sat 6PM results | Held-out AUC, diversity, structure, near-copy output + actual denominators + failure table. |
| #07 | [P1] Add MiniLM semantic distance offline | Rahul | Sat afternoon | Within-intent spread and nearest-neighbor metrics; real reference comparisons; charts; threshold explicit. |
| #08 | [P0] Produce final run and reproducibility manifest | Amrit + Rahul | Sat 5PM | Actual 6×20 run or disclosed shortfall; CSV, batch logs, metrics JSON, model/prompt/settings, failure examples. |
| #09 | [P0] Ethics, attribution, blind human audit | Shreeja | Sat 6PM | CC BY attribution, 20+20 blind set + 2 independent raters if possible, specific 3+ risks and safeguards. |
| #10 | [P0] Dashboard and failure explorer for actual run | Geeth | Sat evening | Four metrics with human-readable explanation; real failure samples; no fake values. |
| #11 | [P0] 11-slide deck, references, 10-min rehearsal | Shreeja coordinates; all supply | Sat 9PM | Actual results, architecture, demo, ethics, slide owners, ≤10 min; backup video recorded. |
| #12 | [P0] Final README, deploy proof, Q&A, individual statements | Abhay + everyone | Saturday freeze | GitHub setup/architecture/evaluation-set readme, code frozen ~10PM, video works, 5 individual paragraphs prepared privately. |

## PR template
```
Closes #<issue>
Owner:
Summary:
Changed files/contracts:
Proof (tests, sample outputs, screenshot):
Data leakage/privacy controls checked:
Unresolved risks:
Reviewer:
```

## Meeting/communication cadence
- Friday kickoff: 15-minute charter, issue assignment, model/data/hosting smoke tests.
- Saturday noon: each owner posts demo link/PR, test result, blocker; integrator declares end-to-end skeleton status.
- Saturday 6 PM: Rahul posts actual metric file, Shreeja posts ethics + audit; all reconcile denominators and slide charts.
- Saturday 10 PM: lead marks code freeze; only bugfixes and presentation preparations.
- Sunday morning: 2 timed rehearsals and offline backup check.

## Suggested commit/branch conventions
`feat/generator-amrit`, `feat/streamlit-geeth`, `feat/eval-rahul`, `docs/risk-shreeja`, `docs/pitch-abhay` and commit subjects `feat:`, `fix:`, `docs:`, `test:`. Do not commit `.env`, any API token, giant model files, or blind audit answer key made public before ratings are complete.