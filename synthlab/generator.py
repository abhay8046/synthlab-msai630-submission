"""Public-seed LLM generation with novelty checks and honest batch accounting.

Real data must come from a live model. Retry shortfalls at most once;
never silently fill with fixture examples. The fixed public train/test
split and downstream evaluation methods remain unchanged.
"""
from __future__ import annotations

import json
import os
import secrets
from typing import Any
import pandas as pd
from .novelty import most_similar

LENGTH_RANGES = {"short": (8, 20), "detailed": (25, 55)}
TONES = ("neutral", "polite", "frustrated")
PROMPT_VERSION = "synthlab-v3-varied-seeds-novelty-2026-10-24"

RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "synthetic_banking_questions",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "records": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {"text": {"type": "string"}},
                        "required": ["text"],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["records"],
            "additionalProperties": False,
        },
    },
}
OPENROUTER_URL = "https://openrouter.ai/api/v1"
DEFAULT_OPENROUTER_MODEL = "openai/gpt-4o-mini"

# Different everyday contexts encourage diversity without inserting
# fictional PII or leaking any held-out test examples.
SCENARIOS = (
    "paying for groceries",
    "a routine mobile app check",
    "a travel preparation task",
    "a purchase at a small shop",
    "a recent payment notification",
    "checking a transaction history",
    "a weekday commute",
    "a weekend shopping errand",
    "an attempted ATM withdrawal",
    "a bill payment deadline",
    "an online checkout",
    "a delayed financial update",
    "a card replacement request",
    "a transfer between ordinary accounts",
    "speaking with customer support",
    "an unexpected account message",
)
# This is a lexical review heuristic, not a certified semantic privacy threshold.
GENERATED_SIMILARITY_LIMIT = 0.87
SOURCE_SIMILARITY_LIMIT = 0.96
MAX_RETRY_CALLS_PER_BATCH = 1

def resolve_model() -> str:
    if os.getenv("OPENROUTER_API_KEY", "").strip():
        return os.getenv("OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL).strip() or DEFAULT_OPENROUTER_MODEL
    return os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"

def get_client():
    from openai import OpenAI
    router_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if router_key:
        return OpenAI(api_key=router_key, base_url=OPENROUTER_URL,
                      timeout=75, max_retries=1)
    key = os.getenv("OPENAI_API_KEY", "").strip()
    base = os.getenv("OPENAI_BASE_URL", "").strip()
    if not key and not base:
        raise RuntimeError(
            "Missing OPENROUTER_API_KEY (recommended) or OPENAI_API_KEY. "
            "Set it privately in Streamlit Cloud Secrets."
        )
    return OpenAI(api_key=key or "local-model", base_url=base or None,
                  timeout=75, max_retries=1)

def generate_batch(
    seeds: pd.DataFrame, *, intent: str, tone: str,
    length_band: str, count: int = 4, model: str | None = None,
    client: Any = None, avoid_examples: list[str] | None = None,
) -> tuple[list[dict], dict]:
    if tone not in TONES or length_band not in LENGTH_RANGES:
        raise ValueError("Invalid tone or length band")
    if not 1 <= count <= 6:
        raise ValueError("Request between 1 and 6 records per API call")
    chosen_model = model or resolve_model()
    if os.getenv("OPENROUTER_API_KEY", "").strip() and chosen_model != resolve_model():
        raise ValueError("OpenRouter model is locked by OPENROUTER_MODEL to protect the API budget")
    pool = seeds.loc[seeds["category"] == intent,"text"].dropna().astype(str).tolist()
    if len(pool) < 2:
        raise ValueError(f"At least two public seed examples needed for {intent}")

    rng = secrets.SystemRandom()
    selected = rng.sample(pool, min(5,len(pool)))
    scenes = rng.sample(SCENARIOS, k=min(5,len(SCENARIOS)))
    nonce = secrets.token_hex(6)
    low,high = LENGTH_RANGES[length_band]
    task = {
        "task": "Write distinctly worded, fictional customer-service messages for a banking intent classifier.",
        "intent": intent,
        "customer_mood": tone,
        "length_band": length_band,
        "target_word_count": f"{low} to {high} words",
        "number_of_records": count,
        "public_reference_examples_TOPIC_ONLY_NEVER_COPY": selected,
        "possible_situation_inspiration": scenes,
        "batch_variation_id": nonce,
        "recent_generated_examples_TO_AVOID_REPEATING": list(avoid_examples or [])[-5:],
        "rules": [
            "The selected intent must be unmistakable, not a related but different banking problem.",
            "Write different sentence openings, problems, contexts and customer vocabularies.",
            "Avoid predictable templates and near paraphrases of examples or previous outputs.",
            "Use only situations relevant to the chosen banking intent; inspiration is optional.",
            "Express the requested tone naturally, but no hateful or abusive content.",
            "Never include personal names, account/card numbers, phone numbers, email addresses or other identifiers.",
            "Return exactly the requested number of distinct records as JSON.",
        ],
    }
    completion = (client or get_client()).chat.completions.create(
        model=chosen_model,
        messages=[
            {"role":"system","content":"Create diverse, entirely fictional banking helpdesk texts using the supplied JSON schema."},
            {"role":"user","content":json.dumps(task, ensure_ascii=False)},
        ],
        response_format=RESPONSE_FORMAT,
        temperature=0.9,
        max_tokens=1200,
    )
    message=completion.choices[0].message
    if getattr(message,"refusal",None):
        raise RuntimeError("Model refused the generation request")
    parsed=json.loads(message.content or "")
    objects=parsed.get("records")
    if not isinstance(objects,list):
        raise ValueError("Model response lacked a records array")
    valid=[]
    for obj in objects[:count]:
        if not isinstance(obj,dict) or not isinstance(obj.get("text"),str):
            continue
        cleaned=" ".join(obj["text"].strip().split())
        if cleaned:
            valid.append({
                "text": cleaned,
                "requested_intent": intent,
                "requested_tone": tone,
                "requested_length": length_band,
                "generator_model": chosen_model,
                "prompt_version": PROMPT_VERSION,
                "prompt_variant": nonce,
            })
    return valid,{
        "requested":count,
        "received":len(objects),
        "valid_schema":len(valid),
        "malformed":max(0,min(count,len(objects))-len(valid)),
        "shortfall":max(0,count-len(valid)),
        "prompt_variant":nonce,
        "seed_examples_in_prompt":len(selected),
    }

def plan_batches(per_intent: int, batch_size: int = 4):
    """For a full 20-row study, sample all six tone/length combinations.

    For tiny pilot sizes use one different combination per call, rather than
    generating all four pilot questions with the exact same controls.
    """
    if not 1<=batch_size<=6:
        raise ValueError("Invalid batch size")
    if not 1<=per_intent<=40:
        raise ValueError("Choose 1–40 records per intent")
    settings=[(tone,length) for length in LENGTH_RANGES for tone in TONES]
    if per_intent < len(settings):
        for index in range(per_intent):
            tone,length=settings[index]
            yield (1,tone,length)
        return
    base,extra=divmod(per_intent,len(settings))
    for index,(tone,length) in enumerate(settings):
        remaining=base+int(index<extra)
        while remaining>0:
            count=min(remaining,batch_size)
            yield (count,tone,length)
            remaining-=count

def generate_dataset(
    seeds: pd.DataFrame, intents: list[str], *, per_intent: int = 20,
    model: str | None = None, on_batch=None, client=None,
    batch_size: int = 4,
    fixed_tone: str | None = None,
    fixed_length: str | None = None,
    previous_texts: list[str] | None = None,
) -> tuple[pd.DataFrame,pd.DataFrame]:
    if not 1<=per_intent<=40:
        raise ValueError("For the demo use between 1 and 40 records per intent")
    if not 1<=batch_size<=6:
        raise ValueError("Batch size must be 1 to 6")
    if len(intents)<2 or len(intents)>6:
        raise ValueError("Choose 2 to 6 intent categories")
    if (fixed_tone is None)!=(fixed_length is None):
        raise ValueError("Specify both tone and length or neither")
    if fixed_tone is not None and (fixed_tone not in TONES or fixed_length not in LENGTH_RANGES):
        raise ValueError("Invalid fixed generation controls")
    output,logs=[],[]
    shared_client=client or get_client()
    target=len(intents)*per_intent
    attempted=0
    # Previous session-generated texts are exclusion examples; no server-side
    # database or other users' data is accessed.
    prior=list(previous_texts or [])[-240:]
    all_seen=prior[:]
    all_seeds=seeds["text"].dropna().astype(str).tolist()
    for intent in intents:
        if fixed_tone is None:
            batches=list(plan_batches(per_intent,batch_size))
        else:
            batches=[
                (min(batch_size,per_intent-offset),fixed_tone,fixed_length)
                for offset in range(0,per_intent,batch_size)
            ]
        for batch_number,(count,tone,length) in enumerate(batches):
            accepted=[]
            received=valid_schema=malformed=rejected=api_calls=0
            errors=[]
            prompt_variants=[]
            for attempt in range(MAX_RETRY_CALLS_PER_BATCH+1):
                required=count-len(accepted)
                if required<=0:
                    break
                api_calls+=1
                try:
                    candidate_rows,stats=generate_batch(
                        seeds,intent=intent,tone=tone,length_band=length,
                        count=required,model=model,client=shared_client,
                        avoid_examples=(all_seen + [r["text"] for r in accepted])[-8:],
                    )
                    received+=stats["received"]
                    valid_schema+=stats["valid_schema"]
                    malformed+=stats["malformed"]
                    prompt_variants.append(stats["prompt_variant"])
                    for row in candidate_rows:
                        similar_generated,_=most_similar(
                            row["text"],all_seen+[r["text"] for r in accepted],
                            threshold=GENERATED_SIMILARITY_LIMIT
                        )
                        similar_public,_=most_similar(
                            row["text"],all_seeds,threshold=SOURCE_SIMILARITY_LIMIT
                        )
                        if similar_generated or similar_public:
                            rejected+=1
                        elif len(accepted)<count:
                            accepted.append(row)
                except Exception as exc:
                    errors.append(f"{type(exc).__name__}: {exc}")
                    # Do not burn the entire $2 key retrying authentication or
                    # provider failures; one API exception ends this batch.
                    break
            output.extend(accepted)
            all_seen.extend([r["text"] for r in accepted])
            logs.append({
                "intent":intent,"tone":tone,"length":length,
                "batch_number":batch_number,"requested":count,
                "received":received,"valid_schema":valid_schema,
                "malformed":malformed,"rejected_similar":rejected,
                "accepted_unique":len(accepted),"api_calls":api_calls,
                "shortfall":count-len(accepted),
                "prompt_variants":";".join(prompt_variants),
                "error":" | ".join(errors),
            })
            attempted+=count
            if on_batch:
                on_batch(attempted,target)
    if not output:
        raise RuntimeError("No new records survived generation and similarity checks; inspect batch errors and avoid-example settings")
    return pd.DataFrame(output),pd.DataFrame(logs)
