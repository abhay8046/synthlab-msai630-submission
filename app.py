"""SynthLab: responsible synthetic data generation, evaluation and failure exploration."""
from __future__ import annotations

import json
import os
from pathlib import Path
from secrets import randbelow
from datetime import datetime, timezone

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from synthlab.dataset import DATASET_REPO, INTENTS, load_banking77, prepare_data
from synthlab.generator import generate_dataset, resolve_model
from synthlab.evaluation import evaluate
from synthlab.access import can_generate
from synthlab.evidence import make_evidence_zip, restore_evidence_zip
from synthlab.human_audit import create_blind_audit, score_blind_audit, synthetic_digest

load_dotenv()
st.set_page_config(page_title="SynthLab | Synthetic Data Factory", page_icon="🧪",
                   layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
.block-container { padding-top:1.35rem; max-width:1200px; }
h1,h2,h3 { letter-spacing:-.035em; }
[data-testid="stMetric"] { border:1px solid rgba(128,128,128,.25); padding:1rem;
  border-radius:14px; background:rgba(128,128,128,.04); }
[data-testid="stSidebar"] { border-right:1px solid rgba(128,128,128,.18); }
</style>
""", unsafe_allow_html=True)
st.title("🧪 SynthLab")
st.caption("THE SYNTHETIC DATA FACTORY  ·  MSAI-630 PROJECT 4  ·  UNIVERSITY OF THE CUMBERLANDS")
st.write("Generate fictional banking support questions, then **test how real, diverse, controlled, and non-copied** they actually are.")

@st.cache_data(ttl=3600, show_spinner="Verifying public BANKING77 dataset and SHA-256 checksums...")
def get_public_data():
    return load_banking77()

try:
    train, test = get_public_data()
except Exception as err:
    st.error(f"Public BANKING77 data unavailable or checksum validation failed: {err}")
    st.info("Check external network access to raw.githubusercontent.com. The app refuses to substitute unverified data.")
    st.stop()

with st.sidebar:
    st.subheader("Experiment controls")
    intents = st.multiselect("Customer question categories", options=INTENTS, default=INTENTS)
    seed_per_intent = st.number_input("Public seed questions per category", min_value=3,
                                       max_value=15, value=8)
    per_intent = st.select_slider("Generate per category", options=[4, 8, 12, 16, 20],
                                  value=4)
    router_mode = bool(os.getenv("OPENROUTER_API_KEY", "").strip())
    model = st.text_input(
        "Generation model", value=resolve_model(),
        disabled=router_mode,
        help="OpenRouter model is fixed by OPENROUTER_MODEL to avoid surprise charges."
             if router_mode else "Model ID provided to the API.",
    )
    if router_mode:
        st.caption("Provider: OpenRouter · limited-cost model")
    mode = st.radio("Attribute controls", ["Balanced evaluation", "Controlled live demo"],
                    help="Balanced covers all six tone/length combinations for the formal experiment.")
    if mode == "Controlled live demo":
        fixed_tone = st.selectbox("Customer tone", ["neutral", "polite", "frustrated"], index=2)
        fixed_length = st.selectbox("Message length", ["short", "detailed"], index=0)
    else:
        fixed_tone, fixed_length = None, None
    st.divider()
    st.caption("Data: PolyAI BANKING77 (CC BY 4.0); Casanueva et al. (2020).")
    st.markdown(f"[Public original dataset]({DATASET_REPO})")
    st.caption("The official test split is never used as a prompt seed.")
    st.caption("No Supabase connection is required for this version.")

if len(intents)<2:
    st.warning("Select at least 2 distinct categories.")
    st.stop()
try:
    seeds, real_train, heldout = prepare_data(
        train, test, intents, seed_per_intent=int(seed_per_intent),
    )
except ValueError as err:
    st.error(str(err))
    st.stop()
chosen_spec = (tuple(intents), int(seed_per_intent))
output_directory = Path("results/latest")

def load_frozen_results():
    metrics_path = output_directory / "metrics.json"
    csv_path = output_directory / "synthetic_records.csv"
    details_path = output_directory / "evaluated_records.csv"
    if not (metrics_path.is_file() and csv_path.is_file()):
        return None
    try:
        return {
            "metrics": json.loads(metrics_path.read_text(encoding="utf-8")),
            "generated": pd.read_csv(csv_path),
            "inspected": pd.read_csv(details_path) if details_path.is_file() else None,
            "manifest": json.loads((output_directory / "run_manifest.json").read_text(encoding="utf-8"))
            if (output_directory / "run_manifest.json").is_file() else None,
        }
    except (OSError, ValueError, KeyError) as err:
        st.error(f"Saved evaluation result files could not be read: {err}")
        return None

frozen = load_frozen_results()
current = st.session_state.get("generated")
current_metrics = st.session_state.get("metrics")
can_evaluate_current = (
    isinstance(current, pd.DataFrame) and not current.empty and
    st.session_state.get("spec") == chosen_spec
)
summary_metrics = current_metrics if can_evaluate_current and current_metrics else (
    frozen["metrics"] if frozen else None
)

header_left, header_right, header_third = st.columns(3)
header_left.metric("Public dataset", f"{len(train):,} train / {len(test):,} test")
header_right.metric("Categories selected", len(intents))
header_third.metric("Real experiment status", "Measured" if summary_metrics else "Awaiting LLM run")

tab_overview, tab_generate, tab_eval, tab_fail, tab_human, tab_game, tab_about = st.tabs([
    "Overview", "Generate", "Quality dashboard", "Failure explorer",
    "Human audit", "Spot the fake", "Methods & safety"
])

with tab_overview:
    st.subheader("What does this application do?")
    st.markdown("**Public seed questions** → **controlled LLM generation** → **four independent quality checks** → **failure review**")
    c1,c2 = st.columns(2)
    with c1:
        st.markdown("#### Generation")
        st.write("Choose banking categories and how many messages to synthesize. "
                 "The app asks an LLM for fictional questions with different tones and lengths.")
    with c2:
        st.markdown("#### Evaluation")
        st.write("We measure real-vs-synthetic separation, repetition, whether requested "
                 "attributes are followed, and similarity to public source records.")
    st.info("All computed metrics come from actual input rows. No demo scores or generated messages are invented.")
    if frozen and frozen.get("manifest"):
        st.subheader("Saved experiment provenance")
        manifest = frozen["manifest"]
        st.write(f"**Model:** {manifest.get('llm_model','Unknown')} · "
                 f"**Generated:** {manifest.get('generated_at_utc','Unknown')} · "
                 f"**Records:** {manifest.get('actual_synthetic_count','Unknown')}")
        st.json({"actual_counts_by_intent": manifest.get("actual_counts_by_intent", {}),
                 "batch_failure_count": manifest.get("batch_failure_count"),
                 "generation_shortfall": manifest.get("generation_shortfall")})

with tab_generate:
    st.subheader("Generate fictional support queries")
    st.write(f"Current target: **{len(intents) * per_intent}** fictional messages across "
             f"**{len(intents)}** categories.")
    st.caption("Start by choosing 2 categories × 4 records (8 total). Export the evidence ZIP after evaluating.")
    st.caption("Balanced evaluation cycles through 3 tones × 2 lengths; "
               "controlled live demo forces one chosen tone and length across the new batch.")
    if fixed_tone is not None:
        st.info(f"Controlled demo: {fixed_tone} tone · {fixed_length} length")
    # Require the same protection on Streamlit Community Cloud, Railway, and localhost.
    # Streamlit Community Cloud exposes root-level app secrets as os.environ.
    access_password = os.getenv("SYNTHLAB_GENERATION_PASSWORD", "").strip()
    api_configured = bool(
        os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_BASE_URL")
    )
    if not access_password:
        st.info("Read-only mode: configure SYNTHLAB_GENERATION_PASSWORD in the host's "
                "secret settings to enable LLM generation.")
        supplied = ""
    else:
        supplied = st.text_input(
            "Team-only generation password", type="password",
            help="Protects your OpenAI API billing. Do not share this with public visitors."
        )
    access_ok = can_generate(
        configured_password=access_password,
        supplied_password=supplied,
        has_api_credentials=api_configured,
    )
    if not api_configured:
        st.warning("No LLM API key is configured. Add OPENROUTER_API_KEY "
                   "to Streamlit Cloud Secrets, not the repository.")
    if access_password and not access_ok and api_configured:
        st.caption("Enter the correct team password to enable API generation.")
    if st.button("✨ Generate real LLM records", type="primary", disabled=not access_ok):
        progress_bar = st.progress(0)
        try:
            def on_progress(done, total):
                progress_bar.progress(min(100, int(100 * done / total)))
            with st.spinner("Calling the model; output and errors are tracked per batch..."):
                generated, logs = generate_dataset(
                    seeds, intents, per_intent=int(per_intent),
                    model=model, on_batch=on_progress,
                    fixed_tone=fixed_tone, fixed_length=fixed_length,
                    previous_texts=st.session_state.get("generation_history", []),
                )
            # Avoid reusing exact or strongly similar records when a user clicks
            # Generate again in the SAME Streamlit session (not persisted to a DB).
            history = st.session_state.get("generation_history", [])
            st.session_state["generation_history"] = (list(history) + generated["text"].tolist())[-240:]
            st.session_state.update({
                "generated": generated, "batch_logs": logs,
                "spec": chosen_spec,
                "generation_source": "streamlit_live_llm",
                "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                "requested_record_count": int(len(intents) * per_intent),
            })
            st.session_state.pop("metrics", None)
            st.session_state.pop("evaluated_rows", None)
            st.session_state.pop("fake_pair", None)
            st.session_state.pop("blind_audit", None)
            st.session_state.pop("human_audit_scores", None)
            st.rerun()
        except Exception as err:
            st.error(f"Generation failed: {err}")
    upload = st.file_uploader("Or import a CSV containing actual previously generated records",
                              type=["csv"], key="upload_synthetic")
    if upload and st.button("Load CSV into this session"):
        try:
            rows = pd.read_csv(upload)
            required = {"text", "requested_intent", "requested_tone", "requested_length"}
            if not required.issubset(rows.columns):
                raise ValueError(f"CSV must include: {', '.join(sorted(required))}")
            if len(rows) > 240:
                raise ValueError("Maximum 240 uploaded records per session")
            st.session_state.update({"generated":rows, "spec":chosen_spec,
                                     "generation_source":"imported_csv",
                                     "generated_at_utc":None,
                                     "requested_record_count":None})
            st.session_state.pop("metrics",None)
            st.session_state.pop("evaluated_rows",None)
            st.session_state.pop("fake_pair",None)
            st.session_state.pop("batch_logs",None)
            st.session_state.pop("blind_audit",None)
            st.session_state.pop("human_audit_scores",None)
            st.rerun()
        except Exception as err:
            st.error(str(err))
    st.divider()
    st.markdown("#### Restore a saved study without spending more credits")
    saved_zip = st.file_uploader("Import your downloaded experiment evidence ZIP",
                                 type=["zip"], key="saved_evidence_zip")
    if saved_zip is not None and st.button("Restore this verified experiment ZIP"):
        try:
            restored, inspected_rows, saved_metrics, manifest, restored_logs = restore_evidence_zip(
                saved_zip.getvalue()
            )
            expected_labels = set(intents)
            actual_labels = set(restored["requested_intent"].astype(str))
            if expected_labels != actual_labels:
                raise ValueError(
                    f"Select exactly the categories used in the ZIP first: {', '.join(sorted(actual_labels))}"
                )
            if int(manifest.get("seed_per_intent", -1)) != int(seed_per_intent):
                raise ValueError(
                    f"Set seed questions per category to {manifest.get('seed_per_intent')} before restoring."
                )
            st.session_state.update({
                "generated": restored, "evaluated_rows": inspected_rows,
                "metrics": saved_metrics, "spec": chosen_spec,
                "generation_source": str(manifest.get("generation_source", "restored_study")),
                "generated_at_utc": manifest.get("generated_at_utc"),
                "requested_record_count": manifest.get("requested_record_count"),
            })
            st.session_state.pop("blind_audit", None)
            st.session_state.pop("human_audit_scores", None)
            if restored_logs is not None:
                st.session_state["batch_logs"] = restored_logs
            else:
                st.session_state.pop("batch_logs", None)
            st.rerun()
        except Exception as err:
            st.error(f"Archive could not be restored: {err}")

    if can_evaluate_current:
        st.dataframe(current, use_container_width=True, hide_index=True)
        st.download_button("Download synthetic CSV", current.to_csv(index=False),
                           file_name="synthetic_records.csv", mime="text/csv")
        if "batch_logs" in st.session_state:
            st.download_button("Download batch errors / statistics",
                st.session_state["batch_logs"].to_csv(index=False),
                file_name="batch_log.csv", mime="text/csv")
    elif frozen:
        st.subheader("Saved actual experiment records")
        st.dataframe(frozen["generated"].head(40),hide_index=True,use_container_width=True)
        st.download_button("Download saved synthetic CSV",
                           frozen["generated"].to_csv(index=False),
                           file_name="synthetic_records.csv",mime="text/csv")

with tab_eval:
    st.subheader("Four-axis quality evaluation")
    if can_evaluate_current:
        if st.button("Evaluate current generated records", type="primary"):
            try:
                with st.spinner("Running blinded source classifier, intent check, diversity and nearest-neighbor analysis..."):
                    computed, inspected, matched = evaluate(seeds, real_train, heldout, current)
                st.session_state["metrics"] = computed
                st.session_state["evaluated_rows"] = inspected
                st.success(f"Evaluated {len(inspected)} actual records.")
            except Exception as err:
                st.error(f"Evaluation failed: {err}")
    metrics = st.session_state.get("metrics") if can_evaluate_current else None
    if not metrics and frozen:
        metrics = frozen["metrics"]
    if metrics:
        def show_pct(name):
            value=metrics.get(name)
            return f"{value:.1%}" if isinstance(value,(float,int)) else "Not measured"
        def show_auc(name):
            value=metrics.get(name)
            return f"{value:.3f}" if isinstance(value,(float,int)) else "Not measured"
        a,b,c,d = st.columns(4)
        a.metric("Fidelity · AUC",show_auc("fidelity_auc"))
        b.metric("Diversity · duplicates",show_pct("diversity_exact_duplicate_rate"))
        c.metric("Structure · intent match",show_pct("structure_intent_match_rate"))
        d.metric("Generalization · near-copy flags",show_pct("generalization_near_copy_rate"))
        st.caption("Fidelity AUC of 0.5 is chance-level source separation; "
                   "0.85 is not a privacy guarantee or universal realism score.")
        st.markdown("#### Repetition and embedding-space spread")
        spread = {
            "Synthetic TF-IDF distance":metrics.get("diversity_synthetic_tfidf_spread"),
            "Matched real TF-IDF distance":metrics.get("diversity_real_tfidf_spread"),
        }
        comparable = {k:v for k,v in spread.items() if v is not None}
        if comparable:
            st.bar_chart(pd.DataFrame({"Mean distance":comparable}))
        col1,col2 = st.columns(2)
        col1.metric("Length-control adherence",show_pct("structure_length_pass_rate"))
        col2.metric("Exact source copies",show_pct("generalization_exact_seed_copy_rate"))
        st.markdown("#### Can a classifier trained ONLY on synthetic records handle real queries?")
        r1,r2,r3=st.columns(3)
        r1.metric("Real-trained → real-test",show_pct("classifier_real_to_real_accuracy"))
        r2.metric("Synthetic-trained → real-test",show_pct("stretch_classifier_synth_to_real_accuracy"))
        r3.metric("Accuracy gap (percentage points)",
                  f"{metrics.get('stretch_accuracy_gap_real_minus_synth',0)*100:.1f}"
                  if metrics.get("stretch_accuracy_gap_real_minus_synth") is not None else "Not measured")
        st.markdown("#### Complete reproducible metrics")
        st.json(metrics,expanded=False)
        st.download_button("Download actual metrics JSON",json.dumps(metrics,indent=2),
                           file_name="metrics.json",mime="application/json")
        # Streamlit Community Cloud containers and sessions are ephemeral.
        current_inspected = st.session_state.get("evaluated_rows") if can_evaluate_current else None
        if can_evaluate_current and current_inspected is not None and metrics == st.session_state.get("metrics"):
            try:
                evidence_bytes = make_evidence_zip(
                    current, current_inspected, metrics,
                    intended_count=st.session_state.get("requested_record_count"),
                    seed_per_intent=int(seed_per_intent),
                    generation_source=st.session_state.get("generation_source", "unknown"),
                    generated_at_utc=st.session_state.get("generated_at_utc"),
                    batch_logs=st.session_state.get("batch_logs"),
                )
                st.download_button(
                    "⬇️ Download complete experiment evidence ZIP",
                    evidence_bytes, file_name="SynthLab_real_experiment_evidence.zip",
                    mime="application/zip", type="primary",
                )
                st.info("Save this ZIP before leaving Streamlit. It contains genuine "
                        "generated data, per-row evaluations, observed failures, "
                        "metrics and the experiment manifest. Send this reviewed ZIP "
                        "back to me so I can add the verified run to private GitHub.")
                if current_inspected["potential_identifier"].any() or current_inspected["flagged_near_copy"].any():
                    st.warning("Some generated records were flagged for possible identifiers or near-copying. "
                               "Inspect them before including them in a public demo.")
            except ValueError as exc:
                st.error(f"Cannot produce evidence ZIP: {exc}")
        semantic_path=output_directory/"semantic_metrics.json"
        if semantic_path.is_file():
            st.markdown("#### Optional semantic embedding results")
            st.json(json.loads(semantic_path.read_text()),expanded=False)
        else:
            st.caption("Semantic MiniLM comparison runs offline: python run_semantic_evaluation.py --output-dir results/latest")
    else:
        st.info("No measured results yet. Generate or import actual records and evaluate them, "
                "or commit verified results/latest files after running run_experiment.py.")
with tab_fail:
    st.subheader("Failure inspection — show the weaknesses")
    inspected = st.session_state.get("evaluated_rows") if can_evaluate_current else None
    if inspected is None and frozen:
        inspected = frozen["inspected"]
    if inspected is None:
        st.info("Run evaluation to inspect actual failed records.")
    else:
        flags = {
            "All records": pd.Series(True,index=inspected.index),
            "Wrong intent": ~inspected["intent_match"],
            "Wrong word count": ~inspected["length_match"],
            "Near-copy flags": inspected["flagged_near_copy"],
            "Exact duplicates": inspected["duplicate_exact"],
            "Potential identifiers": inspected["potential_identifier"],
        }
        selected_flag=st.selectbox("Inspect risk category",list(flags.keys()))
        selection=inspected.loc[flags[selected_flag]]
        st.caption(f"{len(selection)} matching records")
        st.dataframe(selection,hide_index=True,use_container_width=True)
        st.download_button("Download selected inspection rows",selection.to_csv(index=False),
                           file_name="failure_inspection.csv",mime="text/csv")
with tab_human:
    st.subheader("Blind human evaluation")
    st.write("Invite **two independent raters** to classify public real vs LLM-generated questions, "
             "score naturalness from 1–5, and describe the perceived tone. "
             "Raters must not see the private answer key.")
    study_sample = current if can_evaluate_current else (frozen["generated"] if frozen else None)
    if study_sample is None or len(study_sample)<4:
        st.info("Generate at least four real synthetic questions or restore an evaluated study first.")
    else:
        study_hash = synthetic_digest(study_sample)
        choices = [n for n in [4, 8, 12, 16, 20] if n<=len(study_sample)]
        sample_count = st.select_slider("Synthetic questions to blind-rate",
            options=choices, value=max(choices),
            help="The exported CSV also includes the same number of category-matched public real questions.")
        if st.button("Create independent human-rating sheets"):
            try:
                blind, private_key = create_blind_audit(
                    study_sample, heldout, n_synthetic=int(sample_count)
                )
                st.session_state["blind_audit"] = {
                    "hash": study_hash, "blind": blind, "key": private_key
                }
                st.session_state.pop("human_audit_scores", None)
                st.success(f"Prepared {len(blind)} blind questions: {sample_count} synthetic "
                           f"and {sample_count} matched real.")
            except Exception as err:
                st.error(f"Could not create human study: {err}")
        packet = st.session_state.get("blind_audit")
        valid_packet = packet is not None and packet.get("hash")==study_hash
        if valid_packet:
            st.download_button(
                "Download BLIND rating sheet for R1 and R2",
                packet["blind"].to_csv(index=False),
                file_name="synthlab_blind_rater_sheet.csv", mime="text/csv",
            )
            st.caption("Give separate copies of the sheet to your two raters. "
                       "They should use anonymous IDs R1 and R2 and fill every judgment. "
                       "Never show them the answer key until both are finished.")
            if access_ok:
                st.download_button(
                    "Download PRIVATE answer key (team lead only)",
                    packet["key"].to_csv(index=False),
                    file_name="synthlab_private_answer_key.csv",mime="text/csv",
                )
            else:
                st.caption("The private answer key is accessible only after entering "
                           "the team generation password under Generate.")
        st.markdown("#### Score completed questionnaires")
        uploads = st.file_uploader(
            "Upload completed CSVs from both raters (R1 and R2)",
            type=["csv"],accept_multiple_files=True,key="rater_uploads"
        )
        key_upload = st.file_uploader(
            "Optional: upload your saved private answer-key CSV",
            type=["csv"],key="private_answer_key_upload"
        )
        if not access_ok:
            st.caption("Enter the team password under Generate to unlock private audit scoring.")
        if st.button("Compute real human study results", disabled=not access_ok):
            try:
                if not uploads:
                    raise ValueError("Upload at least one genuine completed rating CSV.")
                key = pd.read_csv(key_upload) if key_upload is not None else (
                    packet["key"] if valid_packet else None
                )
                if key is None:
                    raise ValueError("Generate a blind study or upload its matching private key.")
                ratings = pd.concat([pd.read_csv(file) for file in uploads],ignore_index=True)
                human_scores, scored_rows = score_blind_audit(ratings,key)
                st.session_state["human_audit_scores"] = human_scores
                # Only attach human results to the current experiment when the source fingerprint matches.
                if can_evaluate_current and st.session_state.get("metrics"):
                    st.session_state["metrics"]["structure_human_tone_rate"] = human_scores["human_tone_match_rate"]
                    st.session_state["metrics"]["human_audit"] = human_scores
                st.success(f"Scored {human_scores['human_judgment_count']} real human judgments "
                           f"from {human_scores['human_rater_count']} independent rater(s).")
            except Exception as err:
                st.error(f"Human audit scoring failed: {err}")
        if "human_audit_scores" in st.session_state:
            human_scores = st.session_state["human_audit_scores"]
            h1,h2,h3 = st.columns(3)
            h1.metric("Human judgments",human_scores["human_judgment_count"])
            h2.metric("Guess accuracy",f"{human_scores['human_source_guess_accuracy']:.1%}")
            h3.metric("Tone match",f"{human_scores['human_tone_match_rate']:.1%}"
                      if human_scores["human_tone_match_rate"] is not None else "Not scored")
            st.caption(human_scores["human_completion_note"])
            st.json(human_scores)
            st.download_button(
                "Download human audit results JSON",
                json.dumps(human_scores,indent=2),
                file_name="synthlab_human_audit_results.json",
                mime="application/json",
            )

with tab_game:
    st.subheader("Spot the fake: live audience exercise")
    sample=current if can_evaluate_current else (frozen["generated"] if frozen else None)
    if sample is None or sample.empty:
        st.info("Needs real generated records to play. We do not invent examples.")
    else:
        if st.button("New blind pair") or "fake_pair" not in st.session_state:
            row=sample.sample(n=1).iloc[0]
            original=heldout[heldout["category"]==row["requested_intent"]]
            if len(original):
                real=original.sample(n=1)["text"].iloc[0]
                generated_first=bool(randbelow(2))
                st.session_state["fake_pair"] = (
                    [row["text"],real] if generated_first else [real,row["text"]],
                    "A" if generated_first else "B",
                )
                st.session_state["game_revealed"]=False
        if "fake_pair" in st.session_state:
            pair,answer=st.session_state["fake_pair"]
            left,right=st.columns(2)
            left.info(f"**A:** {pair[0]}")
            right.info(f"**B:** {pair[1]}")
            guess=st.radio("Which question is LLM-generated?",["A","B"],horizontal=True)
            if st.button("Reveal answer"):
                st.session_state["game_revealed"]=True
            if st.session_state.get("game_revealed"):
                st.success(f"The synthetic question was {answer}. Your guess was {guess}.")
                st.caption("This game is a teaching demo, not a validated human-fidelity study.")
with tab_about:
    st.markdown("### Methodology and limitations")
    st.markdown("""
**Seed dataset:** PolyAI BANKING77, 10,003 official train / 3,080 official test
queries across 77 labeled banking intents. We use a controlled subset and cite
Casanueva et al. (2020), *Efficient Intent Detection with Dual Sentence Encoders*.

**Fidelity:** train a classifier to predict real vs synthetic on a held-out split.
AUC near chance is evidence only about that classifier and that sample.

**Diversity:** exact duplicates and average within-intent TF-IDF cosine distance.
Optional MiniLM sentence embedding audit runs offline.

**Structure:** independent real-trained intent classifier and word-count adherence.
Tone is not objectively scored automatically. The Human audit tab supports a separate, blinded two-rater study.

**Generalization:** compare every generated question to its closest public training
seed. Thresholds trigger manual review, and passing is **not** proof of privacy.

**Stretch:** train an intent classifier on synthetic queries only, test on the
untouched real test set, and report the gap versus a real-trained baseline.

**Risks:** copying public text, unintended personal identifiers, limited
representation of banking users, uncontrolled tone, model cost abuse, and
over-interpreting automatic realism scores.
""")
    st.warning("Educational research prototype — not suitable for handling real customer records or making privacy guarantees.")
    st.markdown(f"[BANKING77 official source and attribution]({DATASET_REPO})")
    st.caption("Generation is password-protected on Streamlit Cloud and Railway. API keys stay in hosting Secrets, never GitHub.")
