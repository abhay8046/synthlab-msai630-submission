"""Network-free unit tests. All example texts here are fixtures, never real LLM results."""
import pandas as pd
import pytest
from types import SimpleNamespace as Obj
from synthlab.evaluation import word_count, evaluate
from synthlab.generator import generate_batch, generate_dataset
from synthlab.dataset import prepare_data

def fixture_data():
    seeds, train, test, generated = [], [], [], []
    for intent in ["card_not_working", "pending_transfer"]:
        for n in range(6):
            seeds.append({"category":intent, "text":f"Seed question about {intent} example {n}?"})
        for n in range(40):
            train.append({"category":intent,"text":f"Can you fix my {intent.replace('_',' ')} trouble case {n} today?"})
            test.append({"category":intent,"text":f"Please investigate this {intent.replace('_',' ')} problem at time {n}."})
        for n in range(12):
            generated.append({
                "requested_intent":intent,
                "text":f"I have a {intent.replace('_',' ')} question for my bank at hour {n}.",
                "requested_tone":"neutral", "requested_length":"short",
            })
    return tuple(map(pd.DataFrame,(seeds,train,test,generated)))

class FakeAPI:
    def __init__(self):
        self.chat=Obj(completions=Obj(create=lambda **kwargs:Obj(
            choices=[Obj(message=Obj(
                content='{"records":[{"text":"My card keeps getting declined in stores, can you please help me?"}]}',
                refusal=None))])))

def test_word_count():
    assert word_count("My card is not working today.") == 6
    assert word_count("") == 0

def test_generate_batch_strict_contract_mocked():
    seeds=pd.DataFrame([
        {"category":"card_not_working","text":"My card fails when I pay."},
        {"category":"card_not_working","text":"Why doesn't my payment card work?"}])
    rows,stats=generate_batch(seeds,intent="card_not_working",tone="neutral",
        length_band="short",count=1,client=FakeAPI())
    assert len(rows)==1 and stats["valid_schema"]==1
    assert rows[0]["prompt_version"].startswith("synthlab-v3")
    assert rows[0]["requested_intent"]=="card_not_working"

def test_generation_shortfall_is_logged_not_hidden():
    seeds=pd.DataFrame([
        {"category":"card_not_working","text":"Why won't my card work?"},
        {"category":"card_not_working","text":"My card doesn't work at checkout."},
        {"category":"pending_transfer","text":"Why is my transfer pending?"},
        {"category":"pending_transfer","text":"I have an unsettled transfer."}
    ])
    samples,logs=generate_dataset(seeds,["card_not_working","pending_transfer"],
        per_intent=4,client=FakeAPI())
    # The fake model returns exactly the same answer on every call. Only
    # one unique text should survive; never pad the result or claim 8 rows.
    assert len(samples)==1
    assert int(logs["requested"].sum())==8
    assert int(logs["shortfall"].sum())==7
    assert int(logs["rejected_similar"].sum())>0

def test_evaluation_all_four_axes():
    seeds,train,test,generated=fixture_data()
    metrics,rows,real=evaluate(seeds,train,test,generated)
    assert metrics["n_synthetic"]==24
    assert len(rows)==len(real)==24
    assert 0 <= metrics["diversity_exact_duplicate_rate"] <= 1
    assert 0 <= metrics["structure_intent_match_rate"] <= 1
    assert 0 <= metrics["generalization_near_copy_rate"] <= 1
    assert metrics["stretch_classifier_synth_to_real_accuracy"] is not None
    assert "nearest_seed_text" in rows.columns
    assert "potential_identifier" in rows.columns

def test_exact_copies_flagged():
    seeds,train,test,generated=fixture_data()
    generated.loc[0,"text"]=seeds.loc[0,"text"]
    metrics,rows,_=evaluate(seeds,train,test,generated)
    assert bool(rows.loc[0,"exact_seed_copy"])
    assert metrics["generalization_exact_seed_copy_rate"] > 0

def test_seed_is_removed_from_training():
    train=pd.DataFrame([
      {"category":"a","text":f"alpha example {i}"} for i in range(12)
    ]+[{"category":"b","text":f"beta example {i}"} for i in range(12)])
    test=pd.DataFrame([
      {"category":"a","text":f"alpha test {i}"} for i in range(8)
    ]+[{"category":"b","text":f"beta test {i}"} for i in range(8)])
    seeds,real_train,heldout=prepare_data(train,test,["a","b"],seed_per_intent=4)
    assert len(seeds)==8
    assert len(real_train)==16
    assert len(heldout)==16
    assert not set(seeds["text"]) & set(real_train["text"])

def test_evaluation_rejects_unknown_intent():
    seeds,train,test,generated=fixture_data()
    generated.loc[0,"requested_intent"]="unknown_intent"
    with pytest.raises(ValueError,match="Unknown requested intent"):
        evaluate(seeds,train,test,generated)


def test_balanced_experiment_uses_all_six_attribute_combinations():
    from synthlab.generator import plan_batches
    batches=list(plan_batches(20,4))
    assert sum(count for count,_,_ in batches)==20
    assert len({(tone,length) for _,tone,length in batches})==6
    assert max(count for count,_,_ in batches)<=4

def test_fixed_demo_respects_selected_tone_and_length():
    seeds=pd.DataFrame([
        {"category":"card_not_working","text":"Why won't my card work?"},
        {"category":"card_not_working","text":"My card doesn't work at checkout."},
        {"category":"pending_transfer","text":"Why is my transfer pending?"},
        {"category":"pending_transfer","text":"I have an unsettled transfer."}
    ])
    _,logs=generate_dataset(seeds,["card_not_working","pending_transfer"],
        per_intent=4,client=FakeAPI(),fixed_tone="frustrated",fixed_length="detailed")
    assert set(logs["tone"])=={"frustrated"}
    assert set(logs["length"])=={"detailed"}


def test_small_balanced_run_uses_distinct_tone_and_length_settings():
    from synthlab.generator import plan_batches
    planned=list(plan_batches(4,4))
    assert sum(n for n,_,_ in planned)==4
    assert len({(tone,length) for _,tone,length in planned})==4
    assert set(length for _,_,length in planned)=={"short","detailed"}


def test_previous_run_records_are_excluded_from_same_session():
    seeds=pd.DataFrame([
        {"category":"card_not_working","text":"Why won't my card work?"},
        {"category":"card_not_working","text":"My card doesn't work at checkout."},
        {"category":"pending_transfer","text":"Why is my transfer pending?"},
        {"category":"pending_transfer","text":"I have an unsettled transfer."}
    ])
    already_seen="My card keeps getting declined in stores, can you please help me?"
    with pytest.raises(RuntimeError,match="No new records survived"):
        generate_dataset(
            seeds,["card_not_working","pending_transfer"],
            per_intent=4,client=FakeAPI(),previous_texts=[already_seen]
        )
