"""A genuine blind human audit: generate tasks and score independent raters.

The source/label key MUST NOT be given to raters before they complete scoring.
No human ratings are simulated or fabricated in this module.
"""
from __future__ import annotations

import hashlib
import pandas as pd


RATING_FIELDS = (
    "sample_id", "rater_id", "guess_real_or_synthetic",
    "naturalness_1_to_5", "observed_tone", "comments",
)
GUESS_VALUES = {"real", "synthetic"}
TONE_VALUES = {"neutral", "polite", "frustrated", "unclear"}


def synthetic_digest(synthetic: pd.DataFrame) -> str:
    """Stable fingerprint used to tie human scores to the evaluated dataset."""
    required = {"text", "requested_intent"}
    if not required.issubset(synthetic):
        raise ValueError("Synthetic dataset must have text and requested_intent")
    return hashlib.sha256(
        synthetic[["text", "requested_intent"]].to_csv(index=False).encode("utf-8")
    ).hexdigest()


def create_blind_audit(
    synthetic: pd.DataFrame,
    heldout_real: pd.DataFrame,
    n_synthetic: int = 20,
    seed: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build matched synthetic/real questions and separate private answer key.

    Uses the official held-out real examples matched to synthetic intent counts.
    Does not reveal source, category, or expected tone in the rating sheet.
    """
    if not 4 <= n_synthetic <= 30:
        raise ValueError("Choose between 4 and 30 synthetic examples")
    fields = {"text", "requested_intent", "requested_tone"}
    if not fields.issubset(synthetic):
        raise ValueError(f"Generated records missing {sorted(fields - set(synthetic))}")
    if not {"text", "category"}.issubset(heldout_real):
        raise ValueError("Held-out public dataset needs text and category columns")
    if len(synthetic) < n_synthetic:
        raise ValueError(f"Need {n_synthetic} genuine generated records for the blind audit")
    if synthetic["text"].isna().any() or synthetic["text"].astype(str).str.strip().eq("").any():
        raise ValueError("Blank generated question found")

    # Fixed pseudorandom selection makes audits reproducible from the same file.
    sample = synthetic.sample(n=n_synthetic, random_state=seed)
    real_chunks = []
    for intent, chunk in sample.groupby("requested_intent"):
        pool = heldout_real.loc[heldout_real["category"] == intent]
        if len(pool) < len(chunk):
            raise ValueError(f"Not enough held-out real questions for {intent}")
        real_chunks.append(
            pool.sample(n=len(chunk), random_state=seed).assign(
                source="real", requested_tone="", intent=intent
            )[["text", "source", "requested_tone", "intent"]]
        )
    generated = sample.rename(columns={"requested_intent": "intent"}).copy()
    generated["source"] = "synthetic"
    combined = pd.concat(
        [generated[["text", "source", "requested_tone", "intent"]], *real_chunks],
        ignore_index=True,
    ).sample(frac=1, random_state=seed).reset_index(drop=True)
    combined.insert(0, "sample_id", [f"Q{i:03d}" for i in range(1, len(combined)+1)])
    answer_key = combined[["sample_id", "source", "intent", "requested_tone"]].copy()

    blinded = combined[["sample_id", "text"]].copy()
    blinded.insert(0, "rater_id", "")
    blinded["guess_real_or_synthetic"] = ""
    blinded["naturalness_1_to_5"] = ""
    blinded["observed_tone"] = ""
    blinded["comments"] = ""
    blinded = blinded[["sample_id", "text", "rater_id",
                       "guess_real_or_synthetic", "naturalness_1_to_5",
                       "observed_tone", "comments"]]
    return blinded, answer_key


def score_blind_audit(ratings: pd.DataFrame, answer_key: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    """Score real, completed human ratings; never fill missing or invalid answers.

    Requires complete label and naturalness for each accepted response.
    Tone is optional but only scored when a valid tone was provided on a
    generated question.
    """
    expected = {"sample_id", "rater_id", "guess_real_or_synthetic",
                "naturalness_1_to_5", "observed_tone"}
    if not expected.issubset(ratings):
        raise ValueError(f"Ratings missing columns: {sorted(expected - set(ratings))}")
    if not {"sample_id", "source", "intent", "requested_tone"}.issubset(answer_key):
        raise ValueError("Key missing required audit columns")
    if answer_key["sample_id"].duplicated().any():
        raise ValueError("Duplicate sample IDs in private answer key")
    rated = ratings.copy()
    rated["sample_id"] = rated["sample_id"].astype(str).str.strip()
    rated["rater_id"] = rated["rater_id"].fillna("").astype(str).str.strip()
    rated["guess_real_or_synthetic"] = rated["guess_real_or_synthetic"].fillna("").astype(str).str.lower().str.strip()
    rated["observed_tone"] = rated["observed_tone"].fillna("").astype(str).str.lower().str.strip()
    rated["naturalness_1_to_5"] = pd.to_numeric(rated["naturalness_1_to_5"], errors="coerce")
    # Uncompleted questionnaire rows are not claimed as scored data.
    answered = rated[rated["guess_real_or_synthetic"].isin(GUESS_VALUES) &
                     rated["rater_id"].ne("") &
                     rated["naturalness_1_to_5"].between(1, 5)].copy()
    if answered.empty:
        raise ValueError("No valid completed human judgments; use real/synthetic and naturalness 1–5")
    if answered.duplicated(["rater_id", "sample_id"]).any():
        raise ValueError("Repeated rater/sample responses detected")
    missing_ids = set(answered["sample_id"]) - set(answer_key["sample_id"])
    if missing_ids:
        raise ValueError(f"Unknown sample IDs: {sorted(missing_ids)[:5]}")
    merged = answered.merge(answer_key, on="sample_id", how="inner", validate="many_to_one")
    if len(merged) != len(answered):
        raise ValueError("Unmatched human scoring rows")
    merged["source_correct"] = merged["guess_real_or_synthetic"].eq(merged["source"])

    per_rater = (
        merged.groupby("rater_id")
        .agg(judgments=("sample_id","size"), accuracy=("source_correct","mean"))
        .reset_index().to_dict(orient="records")
    )
    synthetic_rows = merged.loc[merged["source"]=="synthetic"].copy()
    valid_tone = synthetic_rows.loc[
        synthetic_rows["observed_tone"].isin(TONE_VALUES) &
        synthetic_rows["observed_tone"].ne("unclear")
    ]
    agreements = []
    for _, grouped in merged.groupby("sample_id"):
        unique_raters = grouped.drop_duplicates("rater_id")
        if len(unique_raters) >= 2:
            guesses = unique_raters["guess_real_or_synthetic"].tolist()
            agreements.append(float(len(set(guesses))==1))
    summary = {
        "human_judgment_count":int(len(merged)),
        "human_unique_question_count":int(merged["sample_id"].nunique()),
        "human_rater_count":int(merged["rater_id"].nunique()),
        "human_source_guess_accuracy":float(merged["source_correct"].mean()),
        "human_mean_naturalness_1_to_5":float(merged["naturalness_1_to_5"].mean()),
        "human_mean_real_naturalness_1_to_5":float(merged.loc[merged["source"]=="real",
            "naturalness_1_to_5"].mean()) if (merged["source"]=="real").any() else None,
        "human_mean_synthetic_naturalness_1_to_5":float(synthetic_rows["naturalness_1_to_5"].mean())
            if len(synthetic_rows) else None,
        "human_tone_valid_judgment_count":int(len(valid_tone)),
        "human_tone_match_rate":float(valid_tone["observed_tone"].eq(valid_tone["requested_tone"]).mean())
            if len(valid_tone) else None,
        "human_source_guess_rater_agreement_rate":float(sum(agreements)/len(agreements))
            if agreements else None,
        "human_rater_agreement_question_count":len(agreements),
        "human_per_rater":per_rater,
        "human_completion_note":(
            "At least two distinct human raters submitted judgments."
            if merged["rater_id"].nunique()>=2 else
            "Only one independent rater so far; recruit a second rater."
        ),
        "method_limitations":(
            "Volunteer human judgments are not representative of the population, "
            "and classification guessing does not prove data anonymity."
        ),
    }
    return summary, merged
