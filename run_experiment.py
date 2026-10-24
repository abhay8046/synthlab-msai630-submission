"""Run actual generation and evaluation. Never generates fabricated results.

Usage:
  python run_experiment.py --per-intent 20 --output-dir results/latest
  python run_experiment.py --synthetic my_generated.csv --output-dir results/latest
"""
import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from synthlab.dataset import EXPECTED_SHA256, INTENTS, load_banking77, prepare_data
from synthlab.generator import PROMPT_VERSION, generate_dataset, resolve_model
from synthlab.evaluation import evaluate

def json_default(obj):
    if hasattr(obj, "item"):
        return obj.item()
    raise TypeError(f"Not JSON serializable: {type(obj).__name__}")

def main():
    load_dotenv()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--per-intent", type=int, default=20)
    ap.add_argument("--seed-per-intent", type=int, default=8)
    ap.add_argument("--intents", nargs="+", default=INTENTS)
    ap.add_argument("--model", default=resolve_model())
    ap.add_argument("--synthetic", help="Evaluate a previously generated CSV (no API call)")
    ap.add_argument("--output-dir", default="results/latest")
    args = ap.parse_args()
    if not 2 <= len(args.intents) <= 6:
        ap.error("Choose 2–6 intents")
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    train, test = load_banking77()
    seeds, real_train, heldout = prepare_data(
        train, test, args.intents, seed_per_intent=args.seed_per_intent,
    )
    if args.synthetic:
        synthetic = pd.read_csv(args.synthetic)
        logs = None
        generation_type = "supplied_existing_csv"
    else:
        synthetic, logs = generate_dataset(
            seeds, args.intents, per_intent=args.per_intent, model=args.model,
            on_batch=lambda done, total: print(f"Generation attempted {done}/{total}"),
        )
        generation_type = ("openrouter_live_generation"
                           if os.getenv("OPENROUTER_API_KEY") else "openai_compatible_live_generation")
        logs.to_csv(out / "batch_log.csv", index=False)
    metrics, inspected, matched = evaluate(seeds, real_train, heldout, synthetic)
    flagged = inspected[
        (~inspected["intent_match"]) |
        (~inspected["length_match"]) |
        inspected["flagged_near_copy"] |
        inspected["duplicate_exact"] |
        inspected["potential_identifier"]
    ].copy()
    synthetic.to_csv(out / "synthetic_records.csv", index=False)
    inspected.to_csv(out / "evaluated_records.csv", index=False)
    flagged.to_csv(out / "failure_records.csv", index=False)
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2, default=json_default), encoding="utf-8")
    manifest = {
        "dataset": "PolyAI BANKING77 CC BY 4.0; Casanueva et al. 2020",
        "dataset_sha256": EXPECTED_SHA256,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "generation_type": generation_type,
        "llm_model": args.model if not args.synthetic else "read_from_synthetic_csv",
        "prompt_version": PROMPT_VERSION if not args.synthetic else "read_from_synthetic_csv",
        "intent_categories": args.intents,
        "seed_per_intent": args.seed_per_intent,
        "requested_per_intent": args.per_intent if not args.synthetic else None,
        "actual_counts_by_intent": {k:int(v) for k,v in synthetic["requested_intent"].value_counts().items()},
        "actual_synthetic_count": len(synthetic),
        "batch_failure_count": int(logs["error"].fillna("").astype(str).ne("").sum()) if logs is not None else None,
        "generation_shortfall": int(logs["shortfall"].sum()) if logs is not None else None,
        "source_file_sha256": hashlib.sha256((out / "synthetic_records.csv").read_bytes()).hexdigest(),
        "ethics_note": "Synthetic records do not guarantee privacy and should not be treated as real customer data.",
    }
    (out / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Saved {len(synthetic)} genuine generated rows to {out}")
    print(f"Fidelity AUC: {metrics['fidelity_auc']} | Intent match: {metrics['structure_intent_match_rate']:.2%}")
    if manifest["generation_shortfall"]:
        print(f"WARNING: {manifest['generation_shortfall']} records missing/invalid. Do not present the requested count as actual.")

if __name__ == "__main__":
    main()
