"""Checksum, schema, and seed leakage tests without network calls."""
import hashlib
import pandas as pd
import pytest
from synthlab import dataset

def test_checksum_and_schema_validation(monkeypatch):
    csv=b"text,category\nHello there,intent_a\nNeed support,intent_b\n"
    monkeypatch.setitem(dataset.EXPECTED_SHA256,"train",hashlib.sha256(csv).hexdigest())
    monkeypatch.setitem(dataset.EXPECTED_ROWS,"train",2)
    df=dataset.parse_dataset_csv(csv,"train")
    assert len(df)==2
    with pytest.raises(ValueError,match="checksum changed"):
        dataset.parse_dataset_csv(csv+b"tampered","train")

def test_seed_and_test_never_overlap():
    train=pd.DataFrame(
        [{"category":c,"text":f"{c} training {i}"} for c in ["a","b"] for i in range(12)]
    )
    test=pd.DataFrame(
        [{"category":c,"text":f"{c} heldout {i}"} for c in ["a","b"] for i in range(5)]
    )
    # One exact training/test duplicate should never be picked as a prompt seed.
    train.loc[0,"text"]=test.loc[0,"text"]
    seeds,remaining,heldout=dataset.prepare_data(train,test,["a","b"],seed_per_intent=4)
    assert len(seeds)==8
    assert not set(seeds["text"]) & set(heldout["text"])
    assert not set(seeds["text"]) & set(remaining["text"])
