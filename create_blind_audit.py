"""Create blind human audit, separated from answer key."""
import argparse
import pandas as pd
from synthlab.dataset import load_banking77

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--synthetic",required=True)
    parser.add_argument("--n",type=int,default=20)
    parser.add_argument("--prefix",default="outputs/blind_audit")
    args=parser.parse_args()
    synthetic=pd.read_csv(args.synthetic)
    if len(synthetic)<args.n:raise ValueError("Not enough generated examples")
    selection=synthetic.sample(n=args.n,random_state=42)
    _,real=load_banking77()
    blocks=[]
    for intent,group in selection.groupby("requested_intent"):
        pool=real[real["category"]==intent]
        blocks.append(pool.sample(n=len(group),random_state=42)[["text"]].assign(
            source="real",intent=intent,requested_tone=""))
    all_rows=pd.concat([selection[["text","requested_intent","requested_tone"]]
       .rename(columns={"requested_intent":"intent"}).assign(source="synthetic"),*blocks],
       ignore_index=True).sample(frac=1,random_state=42).reset_index(drop=True)
    all_rows.insert(0,"sample_id",[f"Q{i:03d}" for i in range(1,len(all_rows)+1)])
    key=all_rows[["sample_id","source","intent","requested_tone"]]
    questions=all_rows[["sample_id","text"]].copy()
    for column in ["rater_id","guess_real_or_synthetic","naturalness_1_to_5",
                    "observed_tone_neutral_polite_frustrated"]:questions[column]=""
    questions.to_csv(args.prefix+"_questions.csv",index=False)
    key.to_csv(args.prefix+"_answer_key_KEEP_PRIVATE.csv",index=False)
    print(f"Created {len(questions)} blinded prompts; keep key private.")

if __name__=="__main__":main()
