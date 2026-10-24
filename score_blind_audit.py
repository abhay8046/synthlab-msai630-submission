"""Score human guesses against the privately retained audit answer key."""
import argparse
import pandas as pd

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--ratings",required=True)
    parser.add_argument("--key",required=True)
    args=parser.parse_args()
    ratings=pd.read_csv(args.ratings)
    key=pd.read_csv(args.key)
    merged=ratings.merge(key,on="sample_id",how="inner",validate="many_to_one")
    if merged.empty:raise ValueError("No matching answers")
    guesses=merged["guess_real_or_synthetic"].astype(str).str.lower().str.strip()
    valid=merged[guesses.isin(["real","synthetic"])].copy()
    if valid.empty:raise ValueError("No completed guesses")
    accuracy=valid["guess_real_or_synthetic"].str.lower().str.strip().eq(valid["source"]).mean()
    print(f"Blind audit: {len(valid)} judgments, {valid['sample_id'].nunique()} unique texts, accuracy={accuracy:.3f}")
    naturalness=pd.to_numeric(valid["naturalness_1_to_5"],errors="coerce")
    if naturalness.notna().any():
        print(f"Mean naturalness={naturalness.mean():.2f}/5 (n={naturalness.notna().sum()})")
    generated=valid[valid["source"]=="synthetic"]
    observed=generated["observed_tone_neutral_polite_frustrated"].astype(str).str.lower().str.strip()
    requested=generated["requested_tone"].astype(str).str.lower().str.strip()
    nonempty=observed.ne("")
    if nonempty.any():print(f"Human tone control match={observed[nonempty].eq(requested[nonempty]).mean():.3f} (n={nonempty.sum()})")

if __name__=="__main__":main()
