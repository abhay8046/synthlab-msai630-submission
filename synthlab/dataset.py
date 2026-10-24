"""Pinned and auditable BANKING77 dataset ingestion.

BANKING77: Casanueva et al. (2020), CC BY 4.0.
Official source: https://github.com/PolyAI-LDN/task-specific-datasets
The official train and test split MUST stay separate. Generated texts never seed generation.
"""
from __future__ import annotations

import hashlib
import io
import urllib.request
import pandas as pd

DATASET_REPO = "https://github.com/PolyAI-LDN/task-specific-datasets"
TRAIN_URL = "https://raw.githubusercontent.com/PolyAI-LDN/task-specific-datasets/master/banking_data/train.csv"
TEST_URL = "https://raw.githubusercontent.com/PolyAI-LDN/task-specific-datasets/master/banking_data/test.csv"
EXPECTED_SHA256 = {
    "train": "b06e26ac675513959a63135f11b94ea7786ed02da65db93a5650d8838cbc664b",
    "test": "d12d6e3bc4c3103966ae786dc435913c0c563dfa328f5a3646d0e62cfeeb474d",
}
EXPECTED_ROWS = {"train": 10003, "test": 3080}
INTENTS = [
    "card_not_working", "cash_withdrawal_charge", "pending_transfer",
    "card_arrival", "compromised_card", "declined_card_payment",
]
SOURCE = DATASET_REPO

def parse_dataset_csv(raw: bytes, split: str) -> pd.DataFrame:
    if split not in EXPECTED_SHA256:
        raise ValueError(f"Unknown split: {split}")
    actual = hashlib.sha256(raw).hexdigest()
    if actual != EXPECTED_SHA256[split]:
        raise ValueError(
            f"BANKING77 {split} checksum changed ({actual}); do not silently continue. "
            "Verify upstream source and update the pin intentionally."
        )
    frame = pd.read_csv(io.BytesIO(raw))
    if set(frame.columns) != {"text", "category"}:
        raise ValueError(f"Unexpected {split} columns: {list(frame.columns)}")
    if len(frame) != EXPECTED_ROWS[split]:
        raise ValueError(f"Unexpected {split} row count: {len(frame)}")
    if frame[["text", "category"]].isna().any().any():
        raise ValueError(f"Missing values in {split} split")
    return frame.reset_index(drop=True)

def load_banking77() -> tuple[pd.DataFrame, pd.DataFrame]:
    def fetch(url: str) -> bytes:
        request = urllib.request.Request(url, headers={"User-Agent": "SynthLab/1.0"})
        with urllib.request.urlopen(request, timeout=25) as response:
            return response.read()
    return (
        parse_dataset_csv(fetch(TRAIN_URL), "train"),
        parse_dataset_csv(fetch(TEST_URL), "test"),
    )

def prepare_data(
    train: pd.DataFrame, test: pd.DataFrame, intents: list[str],
    seed_per_intent: int = 8, random_seed: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    chosen = list(dict.fromkeys(intents))
    if len(chosen) < 2:
        raise ValueError("Select at least two different intents")
    if seed_per_intent < 2:
        raise ValueError("At least two seeds per intent required")
    missing = sorted(set(chosen) - set(train["category"]))
    if missing:
        raise ValueError(f"Intents missing in training split: {missing}")
    missing_test = sorted(set(chosen) - set(test["category"]))
    if missing_test:
        raise ValueError(f"Intents missing in held-out test split: {missing_test}")
    train = train[train["category"].isin(chosen)].copy()
    heldout = test[test["category"].isin(chosen)].copy()
    indexes = []
    # Choose seeds which have no exact counterpart in the untouched official test split.
    available_seeds = train.loc[~train["text"].isin(set(heldout["text"]))]
    for label in chosen:
        group = available_seeds.loc[available_seeds["category"] == label]
        if len(group) <= seed_per_intent:
            raise ValueError(f"Not enough training examples for {label}")
        indexes.extend(group.sample(n=seed_per_intent, random_state=random_seed).index)
    seeds = train.loc[indexes].reset_index(drop=True)
    real_train = train.drop(index=indexes)
    # Remove any exact duplicates of chosen prompts from the real classifier training set.
    real_train = real_train.loc[~real_train["text"].isin(set(seeds["text"]))].reset_index(drop=True)
    if set(seeds["text"]) & set(real_train["text"]):
        raise ValueError("Seed leakage into real classifier training data")
    if set(seeds["text"]) & set(heldout["text"]):
        raise ValueError("Seeds overlap with official held-out test data")
    return seeds, real_train, heldout.reset_index(drop=True)
