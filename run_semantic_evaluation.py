"""Optional embedding-space audit: python run_semantic_evaluation.py --output-dir results/latest"""
import argparse
import json
from pathlib import Path
import pandas as pd
from synthlab.dataset import load_banking77,prepare_data
from synthlab.evaluation import matched_real
from synthlab.semantic_eval import compute_semantic_metrics

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output-dir",default="results/latest")
    args=ap.parse_args()
    out=Path(args.output_dir)
    manifest=json.loads((out/"run_manifest.json").read_text())
    synth=pd.read_csv(out/"synthetic_records.csv")
    train,test=load_banking77()
    seeds,_,heldout=prepare_data(train,test,manifest["intent_categories"],
                                 seed_per_intent=manifest["seed_per_intent"])
    matched=matched_real(heldout,synth)
    metrics,rows=compute_semantic_metrics(seeds,matched,synth)
    (out/"semantic_metrics.json").write_text(json.dumps(metrics,indent=2))
    rows.to_csv(out/"semantic_evaluated_records.csv",index=False)
    print(json.dumps(metrics,indent=2))

if __name__=="__main__":main()
