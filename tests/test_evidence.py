"""Evidence artifact tests use only fixed illustrative test fixtures."""
import json
from io import BytesIO
from zipfile import ZipFile

import pandas as pd
import pytest
from synthlab.evidence import make_evidence_zip, restore_evidence_zip

def records():
    raw=pd.DataFrame([
      {"text":"Why is my card blocked?","requested_intent":"card_not_working",
       "requested_tone":"neutral","requested_length":"short",
       "generator_model":"test-model","prompt_version":"test-v1"},
      {"text":"I can't get my card to work!","requested_intent":"card_not_working",
       "requested_tone":"frustrated","requested_length":"short",
       "generator_model":"test-model","prompt_version":"test-v1"}
    ])
    evaluated=raw.copy()
    evaluated["intent_match"]=[True,False]
    evaluated["length_match"]=[True,True]
    evaluated["duplicate_exact"]=[False,False]
    evaluated["flagged_near_copy"]=[False,True]
    evaluated["potential_identifier"]=[False,False]
    evaluated["exact_seed_copy"]=[False,False]
    return raw,evaluated

def test_zip_contains_genuine_only_records_and_metrics():
    raw,evaluated=records()
    logs=pd.DataFrame([{"requested":2,"shortfall":0,"error":""}])
    blob=make_evidence_zip(raw,evaluated,{"n_synthetic":2,"fidelity_auc":0.64},
                           intended_count=2,seed_per_intent=8,
                           generation_source="llm_live",batch_logs=logs)
    with ZipFile(BytesIO(blob)) as z:
        assert set(z.namelist())=={
            "README.txt","synthetic_records.csv","evaluated_records.csv",
            "failure_records.csv","metrics.json","run_manifest.json","batch_log.csv"}
        manifest=json.loads(z.read("run_manifest.json"))
        assert manifest["successful_record_count"]==2
        assert manifest["generator_models"]==["test-model"]
        assert manifest["reported_batch_shortfall"]==0
        assert len(pd.read_csv(z.open("failure_records.csv")))==1
        assert json.loads(z.read("metrics.json"))["fidelity_auc"]==0.64

def test_fails_closed_when_not_evaluated():
    raw,evaluated=records()
    with pytest.raises(ValueError,match="Generate real records"):
        make_evidence_zip(raw,evaluated,{},generation_source="llm_live")

def test_refuses_stale_evaluation():
    raw,evaluated=records()
    evaluated.loc[0,"text"]="different and unrelated"
    with pytest.raises(ValueError,match="do not match"):
        make_evidence_zip(raw,evaluated,{"n_synthetic":2})

def test_refuses_inconsistent_counts():
    raw,evaluated=records()
    with pytest.raises(ValueError,match="different number of records"):
        make_evidence_zip(raw,evaluated,{"n_synthetic":120})


def test_restore_zip_round_trip_without_network():
    raw,evaluated=records()
    blob=make_evidence_zip(raw,evaluated,{"n_synthetic":2,"fidelity_auc":0.52},
        intended_count=2,generation_source="streamlit_live_llm",
        batch_logs=pd.DataFrame([{"requested":2,"shortfall":0,"error":""}]))
    restored,rows,metrics,manifest,logs=restore_evidence_zip(blob)
    assert restored["text"].tolist()==raw["text"].tolist()
    assert rows["intent_match"].tolist()==[True,False]
    assert metrics["fidelity_auc"]==0.52
    assert manifest["generation_source"]=="streamlit_live_llm"
    assert len(logs)==1

def test_restore_rejects_bad_hash():
    raw,evaluated=records()
    blob=make_evidence_zip(raw,evaluated,{"n_synthetic":2})
    with ZipFile(BytesIO(blob)) as z:
        contents={name:z.read(name) for name in z.namelist()}
    contents["synthetic_records.csv"]=b"tampered,untrusted\nvalue,suspect\n"
    out=BytesIO()
    with ZipFile(out,"w") as z:
        for name,data in contents.items():z.writestr(name,data)
    with pytest.raises(ValueError,match="SHA-256"):
        restore_evidence_zip(out.getvalue())
