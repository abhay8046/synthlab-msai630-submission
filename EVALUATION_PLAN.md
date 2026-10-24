# Prespecified Evaluation Protocol (write before running the LLM)

**Research question:** Can an LLM create short customer-service questions that preserve specific banking intents while remaining distinctive and avoiding near-copies of a public reference set?

**Public source:** PolyAI BANKING77, 10,003 official train and 3,080 official test, CC BY 4.0. Credit the source.

**Prespecified pilot:** 6 intentions; 8 seed examples per intent (48 total); 12–20 generated texts per intent (72–120 total); T=0.9; balanced target-intent generation. Test records held out strictly. Random seed 42 for sampling/evaluation; model outputs themselves are stochastic and not made deterministic by this.

**Generation controls:** intent 6 categories; tone (neutral, polite, frustrated); length (short 8–20 words, detailed 25–55 words). No claims about real-data tone/length distribution matching until measured.

**Fidelity:** Train a real-vs-synthetic TF-IDF/logistic-regression classifier on a stratified, class-matched subset; report held-out ROC AUC. Interpretation: near 0.5 harder discrimination, near 1 easier. Record small sample size and confidence limitations.

**Diversity:** Overall exact duplicate fraction and within-intent mean pairwise TF-IDF cosine distance; compare to class-matched real data. High diversity alone can imply off-topic text; inspect examples.

**Structure:** Predicted intent vs requested intent using independently trained real-text classifier. Also report independent classifier's held-out real-test accuracy. Exact length-band compliance via word counts. Conduct blind human tone audit (20–30 examples). Raw batch response schema success percentage comes from generation logs.

**Generalization:** For every generated example, report most similar generation seed using nearest-neighbor TF-IDF cosine. Manually review those scoring 0.85 or above. This threshold is a *screen*, not a privacy proof; near copying can slip through.

**Human realism audit:** Sample 20 real + 20 generated, same category distribution; shuffle/relabel blindly. Have at least 2 raters say real/synthetic and assess naturalness (1–5). Report number evaluated, raw correctness and disagreement. Blind spot-the-fake in live demo is for engagement, not a substitute for this audit.

**Failure analysis:** Show at least one (a) invalid/off-intent query, (b) near-copy or length failure if any emerge, and (c) limitation in tone controllability. If no errors observed at given threshold, report this accurately; do not invent failures.

**Reproducibility:** Save actual raw output CSV, independent metrics JSON, generation counts/model/temperature (0.9)/timestamps, versioned code, prompt, and screenshots; rerun all measurements from outputs.

**Optional stretch:** Train intent classifier *only on synthetic queries*, evaluate on original official real test split and compare with classifier trained on real training data. Report both class-averaged accuracy and gap, with sample sizes and class balance fixed.