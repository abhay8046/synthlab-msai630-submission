# SynthLab — Blind Human Evaluation Runbook

**Goal:** Independent human judgment for Project 4 fidelity and control. The live "spot the fake" game is not a substitute for this study.

## Study design (do not change after seeing scores)

- Reference: official **BANKING77 test split**. Prompt examples are drawn only from its separate training split.
- Use a **frozen actual LLM generation run**. Recommended: all six selected intents, with 20 generated messages/intent.
- In the Streamlit **Human audit** tab, choose **20 synthetic questions**. The app selects **20 matching real** examples, balances real vs synthetic by intent, shuffles and assigns anonymous sample IDs Q001–Q040 with seed 42.
- Download the **BLIND rating sheet**. Send the same sheet separately to **two independent human raters** (R1 and R2), ideally people who haven't generated or inspected the data. Each works independently, not together.
- Separately download the **private answer key** while authenticated with the SynthLab team password. Save it somewhere private; **never share with the raters**. Do not commit this answer key to GitHub.
- Each rater completes a separate CSV copy, with an anonymous ID (R1/R2), *guess_real_or_synthetic* = real or synthetic, *naturalness_1_to_5* = integer from 1 to 5, and *observed_tone* = neutral/polite/frustrated/unclear. Comments are optional. These are human observations, not objective ground truth.
- Once **both raters finish**, team lead enters the private generation password in **Generate**, then uploads both completed CSVs under **Human audit**, and clicks **Compute real human study results**.
- Export the resulting **human audit results JSON** and the main experiment **evidence ZIP** after scoring; the ZIP will include aggregated human metrics if scored in the same session. Human raw ratings and the key remain separate and should not be published without consent.

## Scoring and reporting

The application calculates:
- Real-vs-synthetic guess **accuracy** on answered rows (50% ≈ chance when balanced; not proof of anonymization)
- Mean naturalness (1–5) for all, real-only, and synthetic-only answered rows
- Perceived tone match on **generated** rows with a usable tone label
- Per-rater sample counts and accuracy
- Agreement between raters on samples both answered

Always state how many different **human raters**, **unique questions** and total **judgments** were actually scored. A study with one rater may be reported as incomplete exploratory data, but **does not meet** the two-rater target. A single rater's "spot the fake" live guess is not a formal study.

## Safety & scope

- Never upload identifying financial records: only fictional generated texts and public BANKING77 questions.
- Tell raters that this is an educational evaluation and their anonymous decisions will inform aggregate research statistics. Do not gather names, emails or private customer accounts.
- The answer key includes public-dataset category and requested tone metadata, not any customer's personal account.
- Review any flagged near-copy/identifier rows before public demo.
- Bias, small sample, choice of raters, control instructions and non-independence of source classifier scores remain limitations.
- **Do not fabricate human ratings, citations, percentages, participant counts or complaints.**

## If the study is not completed

Present the four automatic metrics with their actual sample sizes. State: "A two-rater blind study is prepared, but results were not available at demo freeze." Do **not** claim a real human score or pretend that a public live game replaced it.
