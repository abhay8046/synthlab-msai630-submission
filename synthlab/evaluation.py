"""Reproducible four-axis evaluation of genuine generated text.

Heuristics do not prove realism or privacy. TF-IDF is baseline; an optional
MiniLM embedding check lives in semantic_eval.py.
"""
from __future__ import annotations
import re
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from .generator import LENGTH_RANGES

NEAR_COPY_THRESHOLD = 0.85
IDENTIFIER_PATTERN = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b|\b\+?\d[\d ()-]{8,}\d\b"

def word_count(text):
    return len(re.findall(r"\b[\w'-]+\b", str(text)))

def matched_real(test: pd.DataFrame, synth: pd.DataFrame) -> pd.DataFrame:
    parts = []
    for intent, batch in synth.groupby("requested_intent", sort=True):
        pool = test[test["category"] == intent]
        if len(pool) < len(batch):
            raise ValueError(f"Held-out BANKING77 test class {intent} has only {len(pool)} cases; "
                             f"need {len(batch)}. Reduce requested generation.")
        parts.append(pool.sample(n=len(batch), random_state=42))
    return pd.concat(parts, ignore_index=True)

def _model():
    return make_pipeline(
        TfidfVectorizer(ngram_range=(1, 2), max_features=20000),
        LogisticRegression(max_iter=1500, random_state=42),
    )

def fidelity_auc(real: pd.DataFrame, synthetic: pd.DataFrame):
    """AUC of a blinded source-classification model; 0.5 indicates difficulty distinguishing."""
    if len(synthetic) < 20:
        return None
    labels = np.array([0] * len(real) + [1] * len(synthetic))
    strata = ["real:" + name for name in real["category"]] + [
        "synthetic:" + name for name in synthetic["requested_intent"]
    ]
    if pd.Series(strata).value_counts().min() < 4:
        return None
    x_train, x_test, y_train, y_test = train_test_split(
        real["text"].tolist() + synthetic["text"].tolist(), labels,
        test_size=0.35, random_state=42, stratify=strata,
    )
    detector = _model()
    detector.fit(x_train, y_train)
    probabilities = detector.predict_proba(x_test)[:, 1]
    return float(roc_auc_score(y_test, probabilities))

def within_intent_spread(matrix, labels) -> float | None:
    labels = pd.Series(labels).reset_index(drop=True)
    distances = []
    for intent in labels.unique():
        positions = np.flatnonzero((labels == intent).to_numpy())
        if len(positions) < 2:
            continue
        sim = cosine_similarity(matrix[positions])
        distances.extend((1 - sim[np.triu_indices(len(positions), k=1)]).tolist())
    return float(np.mean(distances)) if distances else None

def evaluate(seeds: pd.DataFrame, model_train: pd.DataFrame,
             test: pd.DataFrame, synthetic: pd.DataFrame):
    if synthetic.empty:
        raise ValueError("No genuine generated records to evaluate.")
    required = {"text", "requested_intent", "requested_tone", "requested_length"}
    if not required.issubset(synthetic):
        raise ValueError(f"Generated CSV missing columns: {sorted(required - set(synthetic))}")
    synth = synthetic.copy().reset_index(drop=True)
    if synth["text"].isna().any() or (synth["text"].astype(str).str.strip() == "").any():
        raise ValueError("Generated dataset contains blank records.")
    if not set(synth["requested_intent"]).issubset(set(test["category"])):
        raise ValueError("Unknown requested intent; cannot score fairly.")
    real = matched_real(test, synth)
    real_clf = _model()
    real_clf.fit(model_train["text"], model_train["category"])
    real_test_accuracy = float(accuracy_score(test["category"], real_clf.predict(test["text"])))
    predictions = real_clf.predict(synth["text"])
    synth["predicted_intent"] = predictions
    synth["intent_match"] = predictions == synth["requested_intent"]
    synth["word_count"] = synth["text"].map(word_count)
    synth["length_match"] = synth.apply(
        lambda row: (
            row["requested_length"] in LENGTH_RANGES and
            LENGTH_RANGES[row["requested_length"]][0] <= row["word_count"] <=
            LENGTH_RANGES[row["requested_length"]][1]
        ), axis=1,
    )
    synth["potential_identifier"] = synth["text"].str.contains(
        IDENTIFIER_PATTERN, regex=True, case=False
    )
    synth["duplicate_exact"] = synth["text"].str.strip().str.casefold().duplicated()
    synth["exact_seed_copy"] = synth["text"].str.strip().str.casefold().isin(
        seeds["text"].str.strip().str.casefold()
    )
    vocabulary = TfidfVectorizer(ngram_range=(1, 2), max_features=20000)
    texts = real["text"].tolist() + synth["text"].tolist() + seeds["text"].tolist()
    all_vecs = vocabulary.fit_transform(texts)
    n_real, n_synth = len(real), len(synth)
    rv = all_vecs[:n_real]
    sv = all_vecs[n_real:n_real+n_synth]
    seeds_vec = all_vecs[n_real+n_synth:]
    similarities = cosine_similarity(sv, seeds_vec)
    nearest_ix = similarities.argmax(axis=1)
    synth["nearest_seed_similarity"] = similarities.max(axis=1)
    synth["nearest_seed_text"] = seeds.iloc[nearest_ix]["text"].values
    synth["flagged_near_copy"] = synth["nearest_seed_similarity"] >= NEAR_COPY_THRESHOLD
    synthetic_only_clf = _model()
    if synth["requested_intent"].nunique() > 1:
        synthetic_only_clf.fit(synth["text"], synth["requested_intent"])
        synthetic_to_real = float(accuracy_score(test["category"], synthetic_only_clf.predict(test["text"])))
    else:
        synthetic_to_real = None
    metrics = {
        "n_synthetic": int(n_synth),
        "n_matched_real": int(n_real),
        "n_seed": int(len(seeds)),
        "n_heldout_real": int(len(test)),
        "n_intents": int(synth["requested_intent"].nunique()),
        "fidelity_auc": fidelity_auc(real, synth),
        "fidelity_interpretation": "Near 0.5 means this particular classifier struggled to distinguish sources, not proof of human realism.",
        "diversity_exact_duplicate_rate": float(synth["duplicate_exact"].mean()),
        "diversity_synthetic_tfidf_spread": within_intent_spread(sv, synth["requested_intent"]),
        "diversity_real_tfidf_spread": within_intent_spread(rv, real["category"]),
        "structure_intent_match_rate": float(synth["intent_match"].mean()),
        "structure_length_pass_rate": float(synth["length_match"].mean()),
        "structure_human_tone_rate": None,
        "classifier_real_to_real_accuracy": real_test_accuracy,
        "stretch_classifier_synth_to_real_accuracy": synthetic_to_real,
        "stretch_accuracy_gap_real_minus_synth": (
            real_test_accuracy - synthetic_to_real if synthetic_to_real is not None else None
        ),
        "generalization_exact_seed_copy_rate": float(synth["exact_seed_copy"].mean()),
        "generalization_near_copy_rate": float(synth["flagged_near_copy"].mean()),
        "generalization_max_seed_similarity": float(synth["nearest_seed_similarity"].max()),
        "generalization_mean_seed_similarity": float(synth["nearest_seed_similarity"].mean()),
        "generalization_threshold_tfidf": NEAR_COPY_THRESHOLD,
        "potential_identifier_pattern_rate": float(synth["potential_identifier"].mean()),
        "methodology": {
            "source": "PolyAI BANKING77, official train/test split, public seed subset only",
            "classifier": "TF-IDF unigrams/bigrams + logistic regression, random_state=42",
            "fidelity_test": "Source classifier, stratified random 65/35 split; per-intent matched real/synthetic counts",
            "diversity": "Exact duplicate rate + mean within-intent TF-IDF cosine distance",
            "structure": "Classifier trained on non-seed real training texts, held-out real accuracy shown; tone requires human scoring",
            "generalization": "Nearest public seed cosine similarity with 0.85 heuristic flag; not a privacy proof",
            "stretch": "Model trained on synthetic alone, tested on untouched real test split; no hyperparameter tuning on test",
        },
    }
    return metrics, synth, real
