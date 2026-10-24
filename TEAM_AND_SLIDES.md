# Team charter and slides outline

## Division of labor (names to fill in)

| Recommended role | Owner | Measurable deliverable |
|---|---|---|
| Product lead | TBD | Clear problem/user definition, pitch story, scope freeze |
| Model/prompt engineer | TBD | LLM prompts, generated dataset, failure examples |
| Integration engineer | TBD | Streamlit, CSV download, deploy/run README |
| Evaluation lead | TBD | AUC, spread, duplicates, intent control, manual ratings |
| Ethics/risk lead | TBD | Copying/PII screens, fairness analysis, mitigations |

Some roles can be combined; every domain must have an owner. The instructor recommends but does not require this role split.

## Week-end checklist from professor

- **Friday evening:** kickoff, team charter, architecture sketch, dataset+API confirmed, commit baseline repo.
- **Saturday midday:** end-to-end generation → evaluation skeleton working.
- **Saturday evening:** actual evaluation numbers and inspected failures available.
- **Saturday ~10 PM:** code freeze; slides, README, backup video, rehearsal only.
- **Sunday morning:** 10-minute presentation with live demonstration, 5-minute Q&A.

## 11-slide plan (replace placeholders with real data)

Detailed speaker script, 10:00 timed allocation, backup demo and Q&A: [DEMO_RUNBOOK.md](DEMO_RUNBOOK.md). Blind two-rater evaluation instructions: [HUMAN_AUDIT.md](HUMAN_AUDIT.md).

1. **Title / one-line claim.** SynthLab: When fake data is safe enough to use (and when it is not).
2. **Who it helps.** Model developers need support queries for testing without processing identifiable financial messages.
3. **The challenge.** Fidelity, diversity, structure, generalization pull in different directions.
4. **Dataset.** BANKING77 provenance, official splits, six selected intents, data diagram.
5. **Architecture.** Public training data → sample seed → LLM prompt+controls → parsed CSV → four evaluators → UI.
6. **Generate live.** Inputs: intent/tone/length → table with controlled outputs.
7. **Fidelity + diversity results.** Real vs synthetic discriminator ROC AUC; diversity/duplicate comparisons.
8. **Structure + copying results.** Intent fidelity, length pass, nearest-seed similarity with actual numbers.
9. **What broke.** Screenshots of real model errors, why, how to reduce them.
10. **Ethics and safety.** Risks (copying, PII, bias, overconfidence), concrete mitigations, non-guarantees.
11. **Conclusions, roadmap and individual contributions.** Limits, downstream synthetic→real classifier stretch, what gets tested next.

**Required Sunday artifacts:** live demonstration with recorded backup; PowerPoint of 10–12 slides; GitHub repo with setup/architecture/evaluation set; private one-paragraph individual contribution per student.