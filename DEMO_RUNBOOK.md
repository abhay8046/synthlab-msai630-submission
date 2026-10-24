# SynthLab Sunday presentation — timed 10-minute runbook

**Friday–Sunday, October 23–25, 2026** · Course MSAI-630 Project 4 · Private GitHub `abhay8046/synthlab-msai630-project4`

This script contains **no invented experiment results**. Replace every `[MEASURED ...]` placeholder only with actual data from an exported, validated evidence ZIP.

## 11 slides (10:00 total)

| Slide | Time | Cumulative | Content to display and say |
|---|---:|---:|---|
| 1. SynthLab: The Synthetic Data Factory | 0:30 | 0:30 | One sentence: "We generate fictional customer support questions and test whether they are useful without merely copying their public seeds." |
| 2. Why synthetic data | 0:40 | 1:10 | Model developers need annotated examples for classifier prototyping and stress testing. Real private banking messages would introduce privacy obligations. Public BANKING77 is our testbed, not private customer input. |
| 3. The four things we must verify | 0:55 | 2:05 | **Fidelity:** does it resemble real text? **Diversity:** is it varied? **Structure:** does it obey intent/tone/length controls? **Generalization:** are we copying seeds? Different qualities need different tests. |
| 4. Research dataset & separation | 0:45 | 2:50 | PolyAI BANKING77: 10,003 official train, 3,080 official test, 77 labels. Six selected intent categories, eight train seeds per intent, official test never shown to the generator. Cite Casanueva et al. (2020), CC BY 4.0. |
| 5. Architecture | 1:00 | 3:50 | Public seeds → OpenRouter `openai/gpt-4o-mini` → JSON schema → generated CSV and batch logs → independent four-axis checks → Streamlit dashboard and downloadable evidence. Mention per-key $2 cap, no auto-topup; don't claim zero risk. |
| 6. Live demo | 1:40 | 5:30 | Show protected app, select controls, generate 4–8 requests if budget/connectivity allow; fall back to **verified saved experiment ZIP** to avoid wasting time or failing online. Demonstrate results and 'spot the fake'. |
| 7. Fidelity and diversity | 1:05 | 6:35 | Show **[MEASURED AUC]**, exact duplicates **[MEASURED %]**, TF-IDF/semantic spread and matched-real baseline **[MEASURED values]**. Explain that chance-like discriminator AUC isn't proof of indistinguishability. |
| 8. Structure and copying | 1:10 | 7:45 | Intent-match rate **[MEASURED %]**, length-control **[MEASURED %]**, held-out classifier accuracy **[MEASURED %]**, near-copy threshold **0.85 TF-IDF** and flagged examples. If available show independent human tone results with actual rater count. |
| 9. Actual failure cases | 0:55 | 8:40 | Show **one real observed failure** from evaluated_records.csv: off-intent, too long, near-copy, or accidental identifier. If none arose, say no errors were flagged by these specific checks and discuss sensitivity. No invented failure! |
| 10. Ethics & what this does not prove | 0:55 | 9:35 | A good AUC/near-copy screen does not certify privacy. Risks: copying, bias from banking topics, unrepresentative prompts, abuse of low-quality data. Safeguards: strict public seeds, held-out test, identifiers and nearest-neighbor screens, human audit and disclaimers. |
| 11. Takeaway and limitations | 0:25 | 10:00 | "Generation is easy; evidence that synthetic data is fit for purpose is harder." Note reproducibility ZIP, open limitations, and team contributions. Transition to 5-minute Q&A. |

## Five-minute Q&A prompts

**Q: Isn't this just ChatGPT making fake sentences?**  
A: The generator is only one stage. We independently test held-out real-vs-synthetic fidelity, spread/duplication, attribute control, and nearest training seed similarity, and we report the failures.

**Q: Can synthetic data still expose people's data?**  
A: Yes. This experiment starts from a public licensed dataset, screens copies and identifier patterns, and does **not** claim formal differential privacy or that all possible memorization is prevented.

**Q: How did you avoid data leakage?**  
A: We use 8 examples per intent exclusively from the original public train set, remove them from classifier training, and never include the official test samples in generation prompts. The GitHub CI verifies source hashes and train/seed/test separation.

**Q: Why not just use the model's own confidence to grade realism?**  
A: That risks self-evaluation. We use a separate TF-IDF/logistic regression discriminator and intent classifier plus independent human ratings if completed.

**Q: What is the practical value of the synthetic-only classifier?**  
A: It tests whether a model trained solely on synthetic intent-labeled questions transfers to held-out real BANKING77 questions. Report its accuracy alongside the real-trained baseline; any gap is meaningful only within this controlled evaluation.

**Q: What if the website is offline on Sunday?**  
A: Use the locally saved evidence ZIP and prerecorded walkthrough. The GitHub code and offline evaluated CSV/JSON remain reproducible.

## Required truthful evidence before substituting numbers

- **Target:** 6 × 20 = 120 records. **Actual:** read `run_manifest.json`; label any shortfalls.
- Include OpenRouter model and prompt version, generation date, seed random state 42, and official data source.
- Use actual `metrics.json` and observed failure rows, not a hypothetical "good" case.
- Show human results **only** if real independent raters returned completed sheets.
- Rehearse twice and record a short backup video while website is working.

## Submission checklist

- [ ] Verified live Streamlit URL shared with evaluators
- [ ] Actual full experiment exported as ZIP, checked, and optionally committed in `results/latest/`
- [ ] MiniLM semantic audit run locally/Colab (strongly recommended; explicitly report if not run)
- [ ] Two real human raters completed blind questions if possible
- [ ] 10–12 slides based on actual measured scores and citations
- [ ] Backup demo video, offline playable
- [ ] GitHub README contains setup and evaluation methodology
- [ ] Five individual contribution statements, each factually confirmed by its author
- [ ] 10-minute presentation plus 5-minute Q&A rehearsed
- [ ] Saturday 10 PM code freeze recorded, unless a critical fix is needed
