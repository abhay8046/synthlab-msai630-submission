"""Produce auditable research artifacts from genuine generated data.

This module does NOT generate or fabricate sample data. Artifacts are built only
from supplied LLM outputs and actually computed evaluation measurements.
"""
from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED, BadZipFile
import hashlib
import json
import pandas as pd

from .dataset import EXPECTED_SHA256

REQUIRED_GENERATED = {"text", "requested_intent", "requested_tone", "requested_length"}
REQUIRED_INSPECTED = REQUIRED_GENERATED | {
    "intent_match", "length_match", "duplicate_exact", "flagged_near_copy",
    "potential_identifier", "exact_seed_copy",
}

def _safe_json(value):
    if hasattr(value, "item"):
        return value.item()
    raise TypeError(f"Cannot serialize {type(value).__name__}")

def make_evidence_zip(
    generated: pd.DataFrame, inspected: pd.DataFrame, metrics: dict, *,
    intended_count: int | None = None,
    seed_per_intent: int = 8,
    generation_source: str = "unspecified",
    generated_at_utc: str | None = None,
    batch_logs: pd.DataFrame | None = None,
) -> bytes:
    """Return a ZIP containing genuine records, measured metrics and provenance.

    Refuses to package outputs if source and inspection rows do not align.
    Does not use placeholder measurements.
    """
    if generated.empty or inspected.empty or not metrics:
        raise ValueError("Generate real records and run evaluation before exporting evidence.")
    if not REQUIRED_GENERATED.issubset(generated.columns):
        raise ValueError(f"Generated data missing {sorted(REQUIRED_GENERATED - set(generated.columns))}")
    if not REQUIRED_INSPECTED.issubset(inspected.columns):
        raise ValueError(f"Evaluation data missing {sorted(REQUIRED_INSPECTED - set(inspected.columns))}")
    if len(generated) != len(inspected):
        raise ValueError("Generated and evaluated record counts are different.")
    if not generated["text"].astype(str).reset_index(drop=True).equals(
        inspected["text"].astype(str).reset_index(drop=True)
    ):
        raise ValueError("The evaluated records do not match the generated text, in row order.")
    if int(metrics.get("n_synthetic", -1)) != len(generated):
        raise ValueError("The saved metrics refer to a different number of records.")

    record_counts = {
        str(k): int(v) for k, v in generated["requested_intent"].value_counts().items()
    }
    csv_generated = generated.to_csv(index=False).encode("utf-8")
    csv_inspected = inspected.to_csv(index=False).encode("utf-8")
    failure_mask = (
        (~inspected["intent_match"].astype(bool)) |
        (~inspected["length_match"].astype(bool)) |
        inspected["duplicate_exact"].astype(bool) |
        inspected["flagged_near_copy"].astype(bool) |
        inspected["potential_identifier"].astype(bool) |
        inspected["exact_seed_copy"].astype(bool)
    )
    failures = inspected.loc[failure_mask]
    manifest = {
        "source": "PolyAI BANKING77, original public train/test CSVs (CC BY 4.0)",
        "dataset_source_sha256": EXPECTED_SHA256,
        "generated_at_utc": generated_at_utc,
        "exported_at_utc": datetime.now(timezone.utc).isoformat(),
        "generation_source": generation_source,
        "generator_models": sorted(generated["generator_model"].dropna().astype(str).unique().tolist())
          if "generator_model" in generated else ["unknown - imported CSV"],
        "prompt_versions": sorted(generated["prompt_version"].dropna().astype(str).unique().tolist())
          if "prompt_version" in generated else ["unknown - imported CSV"],
        "seed_per_intent": int(seed_per_intent),
        "requested_record_count": int(intended_count) if intended_count is not None else None,
        "successful_record_count": len(generated),
        "actual_intent_counts": record_counts,
        "reported_batch_shortfall": int(batch_logs["shortfall"].sum())
          if batch_logs is not None and "shortfall" in batch_logs else None,
        "batch_error_count": int(batch_logs["error"].fillna("").astype(str).ne("").sum())
          if batch_logs is not None and "error" in batch_logs else None,
        "generated_csv_sha256": hashlib.sha256(csv_generated).hexdigest(),
        "privacy_disclaimer": "Similarity flags are screens, not proof of privacy; inspect output before publication.",
        "human_study_status": (
            "Measured volunteer human judgments are included in metrics.json."
            if isinstance(metrics.get("human_audit"), dict)
            and metrics["human_audit"].get("human_judgment_count", 0)>0
            else "Not yet measured; independent human raters needed."
        ),
    }
    readme = (
        "SynthLab reproducible experiment evidence\n"
        "======================================\n"
        "All data here must come from actual LLM generation or imported real experiment records.\n"
        "synthetic_records.csv: raw generated texts and requested control attributes.\n"
        "evaluated_records.csv: per-text computed checks, nearest public seed, and flags.\n"
        "failure_records.csv: real observed failure/risk cases, possibly empty.\n"
        "metrics.json: computed evaluation metrics; null means not measured.\n"
        "run_manifest.json: model, prompt, data hashes, counts, and provenance.\n"
        "batch_log.csv: model request errors and requested/received counts, when available.\n"
        "Do not claim that automatic similarity metrics guarantee data privacy.\n"
        "The separate blind human audit is not included in this ZIP.\n"
    )
    payload = BytesIO()
    with ZipFile(payload, "w", ZIP_DEFLATED, compresslevel=6) as z:
        z.writestr("README.txt", readme)
        z.writestr("synthetic_records.csv", csv_generated)
        z.writestr("evaluated_records.csv", csv_inspected)
        z.writestr("failure_records.csv", failures.to_csv(index=False))
        z.writestr("metrics.json", json.dumps(metrics, indent=2, default=_safe_json))
        z.writestr("run_manifest.json", json.dumps(manifest, indent=2, default=_safe_json))
        if batch_logs is not None:
            z.writestr("batch_log.csv", batch_logs.to_csv(index=False))
    return payload.getvalue()


def restore_evidence_zip(payload: bytes):
    """Read only the supported research archive contents; reject inconsistent data.

    Returns (generated, inspected, metrics, manifest, batch_log | None).
    No code from archives is ever executed and only fixed filenames are read.
    """
    if not payload or len(payload) > 10_000_000:
        raise ValueError("Evidence ZIP must be 10 MB or smaller.")
    try:
        with ZipFile(BytesIO(payload), "r") as z:
            members = {item.filename: item for item in z.infolist()}
            allowed = {
                "README.txt", "synthetic_records.csv", "evaluated_records.csv",
                "failure_records.csv", "metrics.json", "run_manifest.json", "batch_log.csv",
            }
            required = {"synthetic_records.csv", "evaluated_records.csv", "metrics.json",
                        "run_manifest.json"}
            if not required.issubset(members) or not set(members).issubset(allowed):
                raise ValueError("ZIP is missing expected evidence files or has unexpected entries.")
            if len(members) != len(z.infolist()) or sum(
                item.file_size for item in members.values()
            ) > 25_000_000:
                raise ValueError("ZIP includes duplicate paths or oversized decompressed data.")
            raw = z.read("synthetic_records.csv")
            inspected_csv = z.read("evaluated_records.csv")
            metrics = json.loads(z.read("metrics.json"))
            manifest = json.loads(z.read("run_manifest.json"))
            if not isinstance(metrics, dict) or not isinstance(manifest, dict):
                raise ValueError("Malformed metrics or manifest.")
            if hashlib.sha256(raw).hexdigest() != manifest.get("generated_csv_sha256"):
                raise ValueError("Generated CSV does not match the original exported SHA-256 digest.")
            if manifest.get("dataset_source_sha256") != EXPECTED_SHA256:
                raise ValueError("Dataset SHA-256 provenance does not match this SynthLab version.")
            generated = pd.read_csv(BytesIO(raw))
            inspected = pd.read_csv(BytesIO(inspected_csv))
            if int(metrics.get("n_synthetic", -1)) != len(generated):
                raise ValueError("Metrics and record counts disagree.")
            if len(inspected) != len(generated):
                raise ValueError("Inspected rows do not match generated count.")
            if not REQUIRED_GENERATED.issubset(generated) or not REQUIRED_INSPECTED.issubset(inspected):
                raise ValueError("Evidence ZIP is missing required research schema columns.")
            if not generated["text"].astype(str).equals(inspected["text"].astype(str)):
                raise ValueError("Generated and evaluated texts disagree.")
            if len(generated) != manifest.get("successful_record_count"):
                raise ValueError("Manifest row count does not agree with generated CSV.")
            logs = pd.read_csv(z.open("batch_log.csv")) if "batch_log.csv" in members else None
            return generated, inspected, metrics, manifest, logs
    except (OSError, ValueError, KeyError, TypeError, BadZipFile) as exc:
        raise ValueError(f"Could not restore a verified SynthLab evidence ZIP: {exc}") from exc
