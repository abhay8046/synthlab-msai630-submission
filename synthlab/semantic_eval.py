"""Optional embedding-space extension, intended for local/Colab execution.

Install requirements-eval.txt. Scores are not certified privacy assurances.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

def compute_semantic_metrics(seeds:pd.DataFrame, real:pd.DataFrame,
                             synthetic:pd.DataFrame, model_name=MODEL_NAME):
    from sentence_transformers import SentenceTransformer
    model=SentenceTransformer(model_name)
    all_text=synthetic["text"].tolist()+real["text"].tolist()+seeds["text"].tolist()
    embeddings=model.encode(all_text,convert_to_numpy=True,normalize_embeddings=True,
                            show_progress_bar=True,batch_size=32)
    n_s,n_r=len(synthetic),len(real)
    sv,rv,pv=embeddings[:n_s],embeddings[n_s:n_s+n_r],embeddings[n_s+n_r:]
    def spread(v,labels):
        values=[]
        labels=pd.Series(labels).reset_index(drop=True)
        for name in labels.unique():
            indexes=np.flatnonzero((labels==name).to_numpy())
            if len(indexes)<2:continue
            sim=v[indexes]@v[indexes].T
            values.extend((1-sim[np.triu_indices(len(indexes),1)]).tolist())
        return float(np.mean(values)) if values else None
    nearest=sv@pv.T
    winners=nearest.argmax(axis=1)
    inspected=synthetic.reset_index(drop=True).copy()
    inspected["semantic_seed_similarity"]=nearest.max(axis=1)
    inspected["semantic_nearest_seed_text"]=seeds.iloc[winners]["text"].values
    # Heuristic threshold is a review trigger, not a privacy boundary.
    inspected["semantic_near_copy_flag"]=inspected["semantic_seed_similarity"]>=0.92
    metrics={
        "embedding_model":model_name,
        "semantic_within_intent_synthetic_spread":spread(sv,synthetic["requested_intent"]),
        "semantic_within_intent_matched_real_spread":spread(rv,real["category"]),
        "semantic_nearest_seed_mean":float(inspected["semantic_seed_similarity"].mean()),
        "semantic_nearest_seed_max":float(inspected["semantic_seed_similarity"].max()),
        "semantic_copy_flag_rate_at_0_92":float(inspected["semantic_near_copy_flag"].mean()),
        "semantic_flag_threshold":0.92,
        "n_synthetic":len(synthetic),
        "n_matched_real":len(real),
        "n_seed":len(seeds),
        "limitation":"Model-based proximity flag; semantic similarity alone cannot prove no memorization or privacy.",
    }
    return metrics,inspected
