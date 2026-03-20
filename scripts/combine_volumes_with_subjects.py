#!/usr/bin/env python3
"""Combine demographic subjects with aggregated volumes for SynthSeg/FastSurfer.

Usage examples:
  python scripts/combine_volumes_with_subjects.py --method synthseg
  python scripts/combine_volumes_with_subjects.py --method fastsurfer
  python scripts/combine_volumes_with_subjects.py --method both
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd


DATA_DIR = Path("/home/mario/Repository/Normal_Alzeihmer/data")
VOLUMES_DIR = DATA_DIR / "volumes"
COMBINED_DIR = DATA_DIR / "combined"
SELECTED_SUBJECTS_FILE = COMBINED_DIR / "combined_datasets_age50plus_with_oasis.csv"


METHOD_FILES = {
    "synthseg": {
        "ADNI": "adni.csv",
        "IXI": "ixi.csv",
        "OASIS2": "oasis2.csv",
        "OASIS3": "oasis3.csv",
        "PPMI": "ppmi.csv",
        "SRPBS": "srpb.csv",
        "AABC": "aabc.csv",
        "FOMO": "fomo.csv",
    },
    "fastsurfer": {
        "ADNI": "adni_fastsurfer.csv",
        "IXI": "ixi_fastsurfer.csv",
        "OASIS2": "oasis2_fastsurfer.csv",
        "OASIS3": "oasis3_fastsurfer.csv",
        "PPMI": "ppmi_fastsurfer.csv",
        "SRPBS": "srpbs_fastsurfer.csv",
        "AABC": "aabc_fastsurfer.csv",
        "FOMO": "fomo_fastsurfer.csv",
    },
}


def infer_dataset(subject_id: str) -> str:
    """Infer dataset from subject ID when explicit dataset column is missing."""
    sid = str(subject_id)

    if sid.startswith("sub-"):
        if "OAS2_" in sid:
            return "OASIS2"
        if "OAS3" in sid or "OASIS3" in sid:
            return "OASIS3"
        if "OAS" in sid:
            return "OASIS3"
        if "IXI" in sid:
            return "IXI"
        if "PPMI" in sid:
            return "PPMI"
        if "SRPBS" in sid or "SRPB" in sid:
            return "SRPBS"
        if "HCA" in sid:
            return "AABC"
        if "PT" in sid or "FOMO" in sid:
            return "FOMO"

    if "_S_" in sid:
        return "ADNI"
    if sid.startswith("OAS2_"):
        return "OASIS2"
    if sid.startswith("OAS"):
        return "OASIS3"
    if sid.startswith("IXI"):
        return "IXI"
    if sid.startswith("HCA"):
        return "AABC"
    if sid.startswith("PT"):
        return "FOMO"

    return "UNKNOWN"


def load_selected_subjects(selected_subjects_file: Path) -> tuple[pd.DataFrame, str]:
    if not selected_subjects_file.exists():
        raise FileNotFoundError(f"Selected subjects file not found: {selected_subjects_file}")

    selected_df = pd.read_csv(selected_subjects_file)
    if "subject_id" in selected_df.columns:
        subject_col = "subject_id"
    elif "Subject" in selected_df.columns:
        subject_col = "Subject"
    else:
        raise ValueError(f"Cannot find subject id column in {selected_subjects_file}")

    if "dataset" not in selected_df.columns:
        selected_df["dataset"] = selected_df[subject_col].apply(infer_dataset)

    # Keep one selected row per dataset+subject to avoid duplicate outputs.
    selected_df = selected_df.drop_duplicates(subset=["dataset", subject_col], keep="first")

    return selected_df, subject_col


def normalize_subject_id(subject_id: object, dataset: str | None = None) -> str:
    """Normalize subject IDs across methods to improve cross-source matching."""
    sid = str(subject_id).strip()
    if not sid:
        return ""

    ds = (dataset or infer_dataset(sid) or "").upper()

    # Remove common BIDS subject prefix when present.
    if sid.startswith("sub-"):
        sid = sid[4:]

    if ds == "IXI":
        # Map forms like sub-100, 100, ixi100 -> IXI100
        m = re.search(r"(\d+)", sid)
        if m:
            return f"IXI{m.group(1)}"
        return sid.upper()

    if ds in {"ADNI", "OASIS2", "OASIS3", "PPMI", "SRPBS", "AABC", "FOMO"}:
        return sid

    return sid


def load_method_volumes(method: str) -> dict[str, pd.DataFrame]:
    volumes_dfs: dict[str, pd.DataFrame] = {}
    print(f"\nLoading {method.upper()} volume files...")

    for dataset, file_name in METHOD_FILES[method].items():
        file_path = VOLUMES_DIR / file_name
        if not file_path.exists():
            print(f"  - {dataset:8s}: missing ({file_name})")
            continue
        df = pd.read_csv(file_path)
        volumes_dfs[dataset] = df
        print(f"  + {dataset:8s}: {len(df):5d} rows ({file_name})")

    return volumes_dfs


def merge_subjects_with_volumes(
    selected_df: pd.DataFrame,
    subject_col: str,
    method: str,
    volumes_dfs: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    matched = []

    print(f"\nMatching subjects for method={method}...")
    for dataset, vol_df in volumes_dfs.items():
        ds_subjects = selected_df[selected_df["dataset"] == dataset].copy()
        if ds_subjects.empty:
            print(f"  - {dataset:8s}: no selected subjects")
            continue

        vol_subject_cols = [c for c in vol_df.columns if "subject" in c.lower()]
        if not vol_subject_cols:
            print(f"  - {dataset:8s}: no subject column in volume file")
            continue

        vol_subject_col = vol_subject_cols[0]
        if vol_subject_col in vol_df.columns:
            # Keep one row per subject to avoid duplicated demographic matches.
            vol_df = vol_df.drop_duplicates(subset=[vol_subject_col], keep="first")

        # Build normalized merge key on both sides (critical for IXI and mixed ID formats).
        ds_subjects["_subject_key"] = ds_subjects[subject_col].apply(
            lambda x: normalize_subject_id(x, dataset)
        )
        vol_df = vol_df.copy()
        vol_df["_subject_key"] = vol_df[vol_subject_col].apply(lambda x: normalize_subject_id(x, dataset))

        # Keep one row per normalized ID to prevent one-to-many joins from format duplicates.
        vol_df = vol_df.drop_duplicates(subset=["_subject_key"], keep="first")

        merged = ds_subjects.merge(
            vol_df,
            on="_subject_key",
            how="inner",
        )
        if "_subject_key" in merged.columns:
            merged = merged.drop(columns=["_subject_key"])
        merged["source_method"] = method

        print(f"  + {dataset:8s}: matched {len(merged):5d}/{len(ds_subjects):5d}")
        matched.append(merged)

    if not matched:
        raise RuntimeError(f"No subjects matched for method={method}")

    return pd.concat(matched, ignore_index=True)


def apply_qc_if_available(df: pd.DataFrame, method: str) -> pd.DataFrame:
    # FastSurfer exports do not contain SynthSeg qc_* columns.
    if method != "synthseg":
        return df.copy()

    qc_thresholds = {
        "qc_hippocampus+amygdala": 0.75,
        "qc_general white matter": 0.75,
        "qc_general grey matter": 0.70,
    }

    out = df.copy()
    print("\nApplying QC filters (SynthSeg)...")
    for qc_col, threshold in qc_thresholds.items():
        if qc_col not in out.columns:
            continue
        n_before = len(out)
        out = out[out[qc_col] >= threshold]
        print(f"  {qc_col} >= {threshold}: removed {n_before - len(out)}")
    return out


def select_and_derive_columns(df: pd.DataFrame, selected_cols: list[str]) -> pd.DataFrame:
    # Preserve all original selected/clinical columns whenever available.
    clinical_cols = [c for c in selected_cols if c in df.columns]

    core_cols = [
        c
        for c in [
            "subject_id",
            "dataset",
            "source_method",
            "age",
            "sex",
            "site",
            "field_strength",
            "field_strength_T",
            "session_id",
        ]
        if c in df.columns and c not in clinical_cols
    ]

    volume_cols_of_interest = [
        "vol_left hippocampus",
        "vol_right hippocampus",
        "vol_left inferior lateral ventricle",
        "vol_right inferior lateral ventricle",
        "vol_total inferior lateral ventricle",
        "vol_total_hippocampus",
        "ilv_to_hippocampal_ratio",
        "vol_left cerebral white matter",
        "vol_right cerebral white matter",
        "vol_left cerebral cortex",
        "vol_right cerebral cortex",
        "vol_left thalamus",
        "vol_right thalamus",
        "vol_total intracranial",
        "vol_brain-stem",
    ]
    volume_cols = [c for c in volume_cols_of_interest if c in df.columns]
    qc_cols = [c for c in df.columns if c.startswith("qc_")]

    out = df[clinical_cols + core_cols + volume_cols + qc_cols].copy()

    if "vol_left hippocampus" in out.columns and "vol_right hippocampus" in out.columns:
        out["vol_total_hippocampus"] = out["vol_left hippocampus"] + out["vol_right hippocampus"]

    if "vol_total_hippocampus" in out.columns and "vol_total intracranial" in out.columns:
        out["vol_hippocampus_normalized"] = out["vol_total_hippocampus"] / out["vol_total intracranial"]

    if (
        "vol_left inferior lateral ventricle" in out.columns
        and "vol_right inferior lateral ventricle" in out.columns
    ):
        out["vol_total inferior lateral ventricle"] = (
            out["vol_left inferior lateral ventricle"] + out["vol_right inferior lateral ventricle"]
        )

    if (
        "vol_total inferior lateral ventricle" in out.columns
        and "vol_total_hippocampus" in out.columns
    ):
        denom = out["vol_total_hippocampus"].replace(0, pd.NA)
        out["ilv_to_hippocampal_ratio"] = out["vol_total inferior lateral ventricle"] / denom

    if "subject_id" in out.columns:
        sort_cols = [c for c in ["subject_id", "session_id"] if c in out.columns]
        out = out.sort_values(sort_cols)

    return out


def run_method(method: str, selected_subjects_file: Path) -> Path:
    print("\n" + "=" * 80)
    print(f"Combining volumes for method: {method.upper()}")
    print("=" * 80)

    selected_df, subject_col = load_selected_subjects(selected_subjects_file)
    selected_cols = selected_df.columns.tolist()
    volumes_dfs = load_method_volumes(method)
    if not volumes_dfs:
        raise RuntimeError(f"No volume files found for method={method}")

    merged = merge_subjects_with_volumes(selected_df, subject_col, method, volumes_dfs)
    filtered = apply_qc_if_available(merged, method)
    final_df = select_and_derive_columns(filtered, selected_cols)

    output_file = COMBINED_DIR / f"combined_volumes_with_subjects_{method}.csv"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    final_df.to_csv(output_file, index=False)

    print(f"\nSaved: {output_file}")
    print(f"Shape: {final_df.shape}")
    if "dataset" in final_df.columns:
        print("Dataset distribution:")
        print(final_df["dataset"].value_counts().to_string())

    return output_file


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Combine subject metadata with volume files.")
    parser.add_argument(
        "--method",
        choices=["synthseg", "fastsurfer", "both"],
        default="both",
        help="Which method to process.",
    )
    parser.add_argument(
        "--selected-subjects",
        type=Path,
        default=SELECTED_SUBJECTS_FILE,
        help=(
            "CSV of selected subjects with at least subject_id (or Subject) and optional dataset column. "
            "Default: data/combined/combined_datasets_age50plus_with_oasis.csv"
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    methods = ["synthseg", "fastsurfer"] if args.method == "both" else [args.method]
    selected_subjects_file = args.selected_subjects

    print(f"Using selected subjects file: {selected_subjects_file}")

    outputs = []
    for method in methods:
        try:
            outputs.append(run_method(method, selected_subjects_file))
        except Exception as exc:
            print(f"\nERROR ({method}): {exc}")

    print("\n" + "=" * 80)
    print("Done")
    print("=" * 80)
    if outputs:
        for out in outputs:
            print(f"  - {out}")
    else:
        raise SystemExit("No outputs produced.")


if __name__ == "__main__":
    main()
