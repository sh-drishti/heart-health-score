"""
prepare_heart_rate_data.py

Purpose:
    Prepare raw heart-rate observations for patient-specific baseline
    experiments without modifying the original dataset.

Outputs:
    prepared_output/
        heart_rate_prepared.csv
        heart_rate_excluded.csv
        heart_rate_duplicate_candidates.csv
        patient_hr_readiness.csv
        daily_hr_coverage.csv
        preparation_report.txt

Important:
    - Does not calculate baselines or generate alerts.
    - Does not use synthetic ground-truth files.
    - Does not silently delete questionable observations.
    - Uses start_timestamp as measurement time.
    - Treats source quality labels and independent checks separately.
"""

from pathlib import Path
import pandas as pd
import re

# ---------------------------------------------------------
# 1. Configuration
# ---------------------------------------------------------

INPUT_FILE=Path("synthetic_health_connect_30d.csv")
OUTPUT_DIR=Path("prepared_output")

MIN_PLAUSIBLE_HR=30
MAX_PLAUSIBLE_HR=220

DUPLICATE_KEY=["patient_id", "start_timestamp", "parameter","value","unit","activity_context",]
# ---------------------------------------------------------
# 2. Helper functions
# ---------------------------------------------------------

def parse_duplicate_reference(notes):
    if pd.isna(notes):
        return None
    match=re.search(r"(?:^|[;\s])duplicate_of=([^;\s]+)",str(notes))
    return match.group(1) if match else None

def get_column(df,name,default=None):
    if name in df.columns:
        return df[name]
    return pd.Series(default, index=df.index)

# ---------------------------------------------------------
# 3. Load and validate input
# ---------------------------------------------------------

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Could not find {INPUT_FILE.resolve()}\n"
            "Place this script beside the CSV or update INPUT_FILE."
        )
    df=pd.read_csv(INPUT_FILE, low_memory=False)
    original_row_count=len(df)
    required_columns={
        "patient_id",
        "record_id",
        "start_timestamp",
        "parameter",
        "value",
    }
    missing_required=required_columns-set(df.columns)
    
    if missing_required:
        raise ValueError(
            f"Input is missing required columns: "
            f"{sorted(missing_required)}"
        )
    df["start_timestamp"]=pd.to_datetime(df["start_timestamp"],errors="coerce", utc=True)
    if "ingested_timestamp" in df.columns:
        df["ingested_timestamp"]=pd.to_datetime(df["ingested_timestamp"],errors="coerce",utc=True)
        
    df["value_numeric"]=pd.to_numeric(df["value"],errors="coerce")
    df["parameter_normalized"]=(df["parameter"].astype("string").str.strip().str.lower())
    df["context_normalized"]=(get_column(df,"activity_context").astype("string").str.strip().str.lower())
    df["source_quality_normalized"]=(get_column(df,"data_quality").astype("string").str.strip().str.lower())
    
    # ---------------------------------------------------------
    # 4. Select instantaneous hr-records
    # ---------------------------------------------------------
    
    hr_mask=df["parameter_normalized"].eq("heart_rate")
    hr=df.loc[hr_mask].copy()
    
    if hr.empty:
        raise ValueError("No records with parameter='heart_rate' were found.")
    
    # ---------------------------------------------------------
    # 5. Independent qulaity checks
    # ---------------------------------------------------------
    
    hr["quality_flags"]=""
    
    def add_flag(mask,flag):
        mask=mask.fillna(False)
        existing=hr.loc[mask,"quality_flags"]
        hr.loc[mask,"quality_flags"]=existing.map(lambda x: f"{x};{flag}" if x else flag)
    
    add_flag(hr["start_timestamp"].isna(),"invalid_timestamp")
    add_flag(hr["value_numeric"].isna(),"missing_or_non_numeric_value")
    add_flag(hr["value_numeric"].notna() & (hr["value_numeric"] < MIN_PLAUSIBLE_HR),"below_exploratory_range")
    add_flag(hr["value_numeric"].notna() & (hr["value_numeric"] > MAX_PLAUSIBLE_HR),"above_exploratory_range")
    add_flag(hr["source_quality_normalized"].eq("questionable"), "source_marked_questionable")
    add_flag(hr["source_quality_normalized"].eq("unavailable"), "source_marked_unavailable")
    add_flag(hr["context_normalized"].isin(["unknown", ""]), "unknown_or_blank_context")
    add_flag(hr["patient_id"].isna(), "missing_patient_id")
    
    hr["has_quality_flag"]=hr["quality_flags"].ne("")
    # Baseline candidate:
    #  - Numeric HR
    #  - Within exploratory screening bounds
    #  - Valid timestamp and patient ID
    #  - Not source-marked questionable/unavailable
    #  - Context labelled resting or sleeping
    #
    # This is an initial analytical candidate definition, not a
    # validated clinical rule. Source context may be imperfect.
    
    eligible_context=hr["context_normalized"].isin(["resting","sleeping"])
    hr["is_baseline_candidate"]=(
        hr["start_timestamp"].notna()
        & hr["patient_id"].notna()
        & hr["value_numeric"].notna()
        & hr["value_numeric"].between(
            MIN_PLAUSIBLE_HR, MAX_PLAUSIBLE_HR, inclusive="both"
        )
        & ~hr["source_quality_normalized"].isin(
            ["questionable", "unavailable"]
        )
        & eligible_context
    )
    
    # -----------------------------------------------------
    # 6. Identify known resync duplicates
    # -----------------------------------------------------
    
    hr["duplicate_of_record_id"]=get_column(hr,"notes").map(parse_duplicate_reference)
    known_duplicate_ids=set(hr.loc[hr["duplicate_of_record_id"].notna(),"record_id"].astype(str))
    hr["is_known_resync_duplicate"]=(hr["duplicate_of_record_id"].notna())
    # Do not discard these records: preserve them and mark them.
    # Exclude known resync copies from baseline candidates to prevent duplicate weighting, while keeping them in the output.
    hr.loc[hr["is_known_resync_duplicate"], "is_baseline_candidate"] = False
    hr.loc[hr["is_known_resync_duplicate"], "quality_flags"
            ] = hr.loc[hr["is_known_resync_duplicate"], "quality_flags"].map(lambda x: f"{x};known_resync_duplicate" if x else
        "known_resync_duplicate")
    hr["has_quality_flag"] = hr["quality_flags"].ne("")
    
    # -----------------------------------------------------
    # 7. Identify possible duplicates for manual review
    # -----------------------------------------------------
    
    # Exact match on measurement-related fields. Identical values at identical timestamps are only candidates; they may be legitimate.
    available_duplciate_keys=[col for col in DUPLICATE_KEY if col in hr.columns]
    hr["is_exact_duplicate_candidate"]=hr.duplicated(subset=available_duplciate_keys,keep=False)
    duplicate_candidates=hr.loc[hr["is_exact_duplicate_candidate"]].copy()
    
    # -----------------------------------------------------
    # 8. Build accepted and excluded datasets
    # -----------------------------------------------------
    
    prepared=hr.sort_values(["patient_id","start_timestamp","record_id"], na_position="last").copy()
    excluded=prepared.loc[~prepared["is_baseline_candidate"]].copy()
    
    # -----------------------------------------------------
    # 9. Daily coverage
    # -----------------------------------------------------
    
    candidate_rows=prepared.loc[prepared["is_baseline_candidate"]].copy()
    candidate_rows["date_utc"]=(candidate_rows["start_timestamp"].dt.strftime("%Y-%m-%d"))
    if not candidate_rows.empty:
        daily_coverage = (
            candidate_rows.groupby(["patient_id", "date_utc"])
            .agg(
                usable_resting_sleeping_readings=("record_id", "count"),
                median_hr=("value_numeric", "median"),
                min_hr=("value_numeric", "min"),
                max_hr=("value_numeric", "max"),
                contexts=("context_normalized",
                        lambda x: ",".join(sorted(x.dropna().unique()))),
            )
            .reset_index()
        )
    else:
        daily_coverage = pd.DataFrame(
            columns=[
                "patient_id", "date_utc",
                "usable_resting_sleeping_readings",
                "median_hr", "min_hr", "max_hr", "contexts"
            ]
        )

    # -----------------------------------------------------
    # 10. Patient readiness summary
    # -----------------------------------------------------

    patient_ids = sorted(hr["patient_id"].dropna().unique().tolist())
    readiness_rows = []
    for patient_id in patient_ids:
        p_all = prepared.loc[prepared["patient_id"] == patient_id]
        p_candidate = p_all.loc[p_all["is_baseline_candidate"]]

        if not p_candidate.empty:
            per_day = p_candidate.groupby(p_candidate["start_timestamp"].dt.strftime("%Y-%m-%d")).size()
            days_with_any = int(len(per_day))
            days_with_10_plus = int((per_day >= 10).sum())
            total_candidates = int(len(p_candidate))
            median_daily_count = float(per_day.median())
        else:
            days_with_any = 0
            days_with_10_plus = 0
            total_candidates = 0
            median_daily_count = 0.0

        readiness_rows.append({
            "patient_id": patient_id,
            "total_hr_records": int(len(p_all)),
            "baseline_candidate_records": total_candidates,
            "days_with_candidate_readings": days_with_any,
            "days_with_at_least_10_candidate_readings": days_with_10_plus,
            "median_candidate_readings_per_observed_day": median_daily_count,
            "known_resync_duplicates": int(
                p_all["is_known_resync_duplicate"].sum()
            ),
            "exact_duplicate_candidate_rows": int(
                p_all["is_exact_duplicate_candidate"].sum()
            ),
            "baseline_readiness_note": (
                "Review coverage before baseline estimation"
                if days_with_10_plus < 7
                else "Coverage may support initial baseline experiments"
            ),
        })

    patient_readiness = pd.DataFrame(readiness_rows)

    # -----------------------------------------------------
    # 11. Write outputs
    # -----------------------------------------------------

    prepared.to_csv(OUTPUT_DIR / "heart_rate_prepared.csv", index=False)
    excluded.to_csv(OUTPUT_DIR / "heart_rate_excluded.csv", index=False)
    duplicate_candidates.to_csv(OUTPUT_DIR / "heart_rate_duplicate_candidates.csv", index=False)
    patient_readiness.to_csv(OUTPUT_DIR / "patient_hr_readiness.csv", index=False)
    daily_coverage.to_csv(OUTPUT_DIR / "daily_hr_coverage.csv", index=False)

    # -----------------------------------------------------
    # 12. Write a compact report
    # -----------------------------------------------------

    lines = [
        "HEART-RATE PREPARATION REPORT",
        "=" * 50,
        f"Input file: {INPUT_FILE.resolve()}",
        f"Original total rows: {original_row_count:,}",
        f"Heart-rate rows: {len(hr):,}",
        f"Patients with HR records: {hr['patient_id'].nunique():,}",
        "",
        "BASELINE CANDIDATE COUNTS",
        "-" * 50,
        f"Candidate observations: {int(hr['is_baseline_candidate'].sum()):,}",
        f"Non-candidate observations: {int((~hr['is_baseline_candidate']).sum()):,}",
        f"Known resync duplicate rows: {int(hr['is_known_resync_duplicate'].sum()):,}",
        f"Exact duplicate candidate rows: {int(hr['is_exact_duplicate_candidate'].sum()):,}",
        "",
        "QUALITY FLAGS",
        "-" * 50,
        f"Rows with one or more flags: {int(hr['has_quality_flag'].sum()):,}",
        f"Missing/non-numeric HR: {int(hr['value_numeric'].isna().sum()):,}",
        f"Below exploratory range: {int((hr['value_numeric'] < MIN_PLAUSIBLE_HR).sum()):,}",
        f"Above exploratory range: {int((hr['value_numeric'] > MAX_PLAUSIBLE_HR).sum()):,}",
        f"Invalid timestamps: {int(hr['start_timestamp'].isna().sum()):,}",
        "",
        "OUTPUTS",
        "-" * 50,
        *[f"- {path.name}" for path in sorted(OUTPUT_DIR.glob("*.csv"))],
        "",
        "INTERPRETATION NOTES",
        "-" * 50,
        "- Original input CSV was not modified.",
        "- Excluded records are retained in heart_rate_excluded.csv.",
        "- Exact duplicate candidates are not automatically deleted.",
        "- Only records labelled resting/sleeping are initial baseline candidates.",
        "- Source quality labels and activity context may be imperfect.",
        "- The 30-220 bpm screen is exploratory, not a clinical threshold.",
        "- No baseline or clinical alert is calculated by this script.",
    ]

    report_text = "\n".join(lines)
    (OUTPUT_DIR / "preparation_report.txt").write_text(report_text, encoding="utf-8")

    print(report_text)
    print(f"\nOutputs saved to: {OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
