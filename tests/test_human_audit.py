"""Offline blind-human-evaluation tests. Fixture ratings are not real study results."""
import pandas as pd
import pytest
from synthlab.human_audit import (
    create_blind_audit, score_blind_audit, synthetic_digest,
)

def inputs():
    records,real=[],[]
    for intent in ["card_not_working", "pending_transfer"]:
        for n in range(12):
            records.append({
                "text":f"Help with a {intent.replace('_',' ')} question number {n} please.",
                "requested_intent":intent, "requested_tone":["neutral","polite","frustrated"][n%3],
            })
        for n in range(30):
            real.append({"text":f"A public real {intent} sample at {n}", "category":intent})
    return pd.DataFrame(records), pd.DataFrame(real)

def test_blind_audit_is_balanced_and_blinded():
    synth,real=inputs()
    blind,key=create_blind_audit(synth,real,n_synthetic=12)
    assert len(blind)==len(key)==24
    assert key["source"].value_counts().to_dict()=={"synthetic":12,"real":12}
    assert key.groupby(["intent","source"]).size().unstack().nunique(axis=1).eq(1).all()
    assert "source" not in blind.columns and "intent" not in blind.columns
    assert "requested_tone" not in blind.columns
    assert blind["sample_id"].is_unique
    assert blind.equals(create_blind_audit(synth,real,n_synthetic=12)[0])
    assert len(synthetic_digest(synth))==64

def test_completed_rater_scoring_and_agreement():
    synth,real=inputs()
    blind,key=create_blind_audit(synth,real,n_synthetic=8)
    ratings=pd.concat([blind.assign(rater_id=rater, guess_real_or_synthetic="synthetic",
                naturalness_1_to_5=4,observed_tone="polite")
                for rater in ["R1","R2"]],ignore_index=True)
    scores,merged=score_blind_audit(ratings,key)
    assert scores["human_rater_count"]==2
    assert scores["human_judgment_count"]==32
    assert scores["human_unique_question_count"]==16
    assert scores["human_source_guess_accuracy"]==0.5
    assert scores["human_source_guess_rater_agreement_rate"]==1.
    assert scores["human_tone_valid_judgment_count"]==16
    assert set(merged["source"])=={"real","synthetic"}

def test_uncompleted_and_invalid_ratings_are_not_fabricated():
    synth,real=inputs()
    blind,key=create_blind_audit(synth,real,n_synthetic=4)
    with pytest.raises(ValueError,match="No valid completed"):
        score_blind_audit(blind,key)
    answered=blind.copy()
    answered.loc[0,"rater_id"]="R1"
    answered.loc[0,"guess_real_or_synthetic"]="real"
    answered.loc[0,"naturalness_1_to_5"]="5"
    scores,_=score_blind_audit(answered,key)
    assert scores["human_judgment_count"]==1
    assert scores["human_rater_count"]==1
    assert scores["human_source_guess_rater_agreement_rate"] is None

def test_duplicate_rater_answer_rejected():
    synth,real=inputs()
    blind,key=create_blind_audit(synth,real,n_synthetic=4)
    one=blind.head(1).assign(rater_id="R1",guess_real_or_synthetic="real",naturalness_1_to_5="4")
    with pytest.raises(ValueError,match="Repeated rater/sample"):
        score_blind_audit(pd.concat([one,one]),key)
