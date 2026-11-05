"""
Profile synthetic_health_connect_30d.csv before developing
patient-specific baselines and continuous monitoring.

Outputs:
    profiling_output/
        profiling_report.txt
        patient_summary.csv
        parameter_summary.csv
        heart_rate_context_summary.csv
        sampling_summary.csv
        data_quality_summary.csv
        daily_coverage.csv
        suspicious_heart_rate.csv
        duplicate_candidates.csv
        heart_rate_distribution.png
        sampling_intervals.png
        patient_coverage.png
        patient_timelines/
            selected patient timelines

This script is exploratory only. It does not modify the input CSV,
calculate baselines, or generate clinical alerts.
"""
from pathlib import Path
import argparse
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------
EXPECTED_COLUMNS = [
    "patient_id",
    "record_id",
    "record_type",
    "parameter",
    "value",
    "unit",
    "start_timestamp",
    "end_timestamp",
    "source_app",
    "source_device",
    "recorded_timestamp",
    "ingested_timestamp",
    "activity_context",
    "data_quality",
    "notes",
]
# Broad data-quality screening bounds for exploratory profiling only.
HR_MIN_PLAUSIBLE = 30
HR_MAX_PLAUSIBLE = 220

# A gap longer than this is reported as a long gap.
LONG_GAP_MINUTES = 60

# Used only to identify patients for diagnostic plots.
TIMELINE_PATIENT_COUNT = 6

# ---------------------------------------------------------
# Utility functions
# ---------------------------------------------------------

def save_text(path,lines):
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    
def section(lines,heading):
    lines.extend(["","="*72,heading,"="*72])
    
def safe_percentage(numerator,denominator):
    if denominator == 0:
        return 0.0
    return 100.0 * numerator / denominator

def load_data(csv_path):
    print(f"Loading: {csv_path}")
    df=pd.read_csv(csv_path, dtype={
        "patient_id": "string",
        "record_id": "string",
        "record_type": "string",
        "parameter": "string",
        "unit": "string",
        "source_app": "string",
        "source_device": "string",
        "activity_context": "string",
        "data_quality": "string",
        "notes": "string",
    },
    low_memory=False,)
    
    missing_columns=sorted(set(EXPECTED_COLUMNS)-set(df.columns))
    extra_columns=sorted(set(df.columns)-set(EXPECTED_COLUMNS))
    
    print(f"Loaded {len(df):,} rows and {len(df.columns)} columns.")
    if missing_columns:
        warnings.warn(f"Missing columns: {missing_columns}")
    if extra_columns:
        warnings.warn(f"Extra columns: {extra_columns}")
        
    for col in ["start_timestamp","end_timestamp","recorded_timestamp","ingested_timestamp"]:
        if col in df.columns:
            df[col]=pd.to_datetime(df[col],errors="coerce",utc=True)
    
    if "value" in df.columns:
        df["value_numeric"]=pd.to_numeric(df["value"],errors="coerce")
    
    return df,missing_columns,extra_columns

# ---------------------------------------------------------
# General summaries
# ---------------------------------------------------------

def build_general_summaries(df,output_dir, report):
    section(report,"1. Dataset Overview")
    report.extend([
        f"Rows: {len(df):,}",
        f"Columns: {len(df.columns):,}",
        f"Unique patients: {df['patient_id'].nunique(dropna=True):,}",
        f"Unique record IDs: {df['record_id'].nunique(dropna=True):,}",
        f"Duplicate record IDs: {df['record_id'].duplicated().sum():,}",
        f"Start timestamp range: {df['start_timestamp'].min()} to "
        f"{df['start_timestamp'].max()}",
        f"Missing patient IDs: {df['patient_id'].isna().sum():,}",
        f"Missing record IDs: {df['record_id'].isna().sum():,}",
    ])
    type_summary=(df["record_type"].fillna("<missing>").value_counts().rename_axis("record_type").reset_index(name="row_count"))
    type_summary.to_csv(output_dir/"record_type_summary.csv",index=False)
    
    parameter_summary=(df.groupby(["parameter","record_type","unit","data_quality"],dropna=False).size().reset_index(name="row_count").sort_values(["parameter","data_quality"]))
    parameter_summary.to_csv(output_dir/"parameter_summary.csv",index=False)
    
    section(report,"2. MISSINGNESS AND SCHEMA")
    
    missingness=pd.DataFrame({
        "column": df.columns,
        "missing_count": [df[col].isna().sum() for col in df.columns]
    })
    missingness["missing_percentage"]=100.0*missingness["missing_count"]/len(df)
    missingness.to_csv(output_dir/"missingness_summary.csv",index=False)
    
    report.append("Column missingness:")
    for _,row in missingness.iterrows():
        report.append(f"  {row['column']}: {int(row['missing_count']):,} "
            f"({row['missing_percentage']:.2f}%)")
    
    # Verify record types and parameters.
    report.append(f"Record types: {df['record_type'].nunique(dropna=True)}")
    report.append(f"Parameters: {df['parameter'].nunique(dropna=True)}")
    report.append(
        f"Quality labels: "
        f"{df['data_quality'].value_counts(dropna=False).to_dict()}"
    )

    return type_summary, parameter_summary

# ---------------------------------------------------------
# Heart-rate quality analysis
# ---------------------------------------------------------

def analyze_heart_rate_quality(df,output_dir,report):
    hr=df.loc[df["parameter"].eq("heart_rate")].copy()
    section(report,"3. HEART RATE QUALITY")
    
    if hr.empty:
        report.append("No heart-rate records found.")
        return hr,pd.DataFrame()
    
    hr["hr"]=pd.to_numeric(hr["value"],errors="coerce")
    
    invalid_numeric = hr["hr"].isna() & hr["data_quality"].ne("unavailable")
    below_range = hr["hr"] < HR_MIN_PLAUSIBLE
    above_range = hr["hr"] > HR_MAX_PLAUSIBLE

    # Flag independently of the source-provided data_quality label.
    hr["screening_flag"] = np.select(
        [
            hr["data_quality"].eq("unavailable"),
            hr["hr"].isna(),
            below_range,
            above_range,
            hr["data_quality"].eq("questionable"),
        ],
        [
            "unavailable",
            "missing_or_non_numeric_value",
            "below_exploratory_range",
            "above_exploratory_range",
            "source_questionable",
        ],
        default="no_basic_screening_flag",
    )

    report.extend([
        f"Heart-rate rows: {len(hr):,}",
        f"Source-labelled valid: {hr['data_quality'].eq('valid').sum():,}",
        f"Source-labelled questionable: "
        f"{hr['data_quality'].eq('questionable').sum():,}",
        f"Source-labelled unavailable: "
        f"{hr['data_quality'].eq('unavailable').sum():,}",
        f"Missing/non-numeric usable values: {invalid_numeric.sum():,}",
        f"Values below {HR_MIN_PLAUSIBLE} bpm: {below_range.sum():,}",
        f"Values above {HR_MAX_PLAUSIBLE} bpm: {above_range.sum():,}",
        f"Minimum numeric HR: {hr['hr'].min()}",
        f"Maximum numeric HR: {hr['hr'].max()}",
    ])
    
    suspicious=hr.loc[hr["screening_flag"].ne("no_basic_screening_flag")].copy()
    suspicious.to_csv(output_dir/"suspicious_heart_rate.csv",index=False)
    
    duplicate_key = [
        "patient_id",
        "parameter",
        "value",
        "unit",
        "start_timestamp",
        "recorded_timestamp",
        "source_app",
        "source_device",
        "activity_context",
    ]
    duplicate_key=[c for c in duplicate_key if c in hr.columns]
    
    hr["duplicate_candidate"] = hr.duplicated(subset=duplicate_key, keep=False)
    duplicate_candidates = hr.loc[hr["duplicate_candidate"]].copy()
    duplicate_candidates.to_csv(output_dir/"duplicate_candidates.csv",index=False)
    
    report.extend([
        f"Basic screening flagged rows: {len(suspicious):,}",
        f"Rows in exact-content duplicate candidate groups: "
        f"{len(duplicate_candidates):,}",
        "Note: duplicate candidates require review; do not automatically "
        "delete them.",
    ])
    
    # Distribution by context and quality.
    usable_range=hr["hr"].between(HR_MIN_PLAUSIBLE,HR_MAX_PLAUSIBLE, inclusive="both")
    
    context_summary=(hr.loc[usable_range].groupby(["activity_context","data_quality"],dropna=False)["hr"].agg(["count","median","mean","std","min","max"]).reset_index())
    context_summary.to_csv(output_dir/"heart_rate_context_summary.csv",index=False)
    
    report.append("\nHeart-rate distribution by context and quality:")
    report.append(context_summary.to_string(index=False))
    
    plot_hr=hr.loc[usable_range,"hr"].dropna()
    
    if not plot_hr.empty:
        plt.figure(figsize=(9, 5))
        plt.hist(plot_hr, bins=50)
        plt.title("Heart-rate distribution (30–220 bpm)")
        plt.xlabel("Heart rate (bpm)")
        plt.ylabel("Number of readings")
        plt.tight_layout()
        plt.savefig(output_dir / "heart_rate_distribution.png", dpi=150)
        plt.close()

    return hr, context_summary

# ---------------------------------------------------------
# Sampling and coverage
# ---------------------------------------------------------

def analyze_sampling(hr,out_dir,report):
    section(report,"4. SAMPLING AND COVERAGE")
    
    if hr.empty:
        report.append("No heart-rate records found; skipping sampling analysis.")
        return pd.DataFrame(), pd.DataFrame()
    
    hr=hr.sort_values(["patient_id","start_timestamp"]).copy()
    
    hr["interval_minutes"] = (hr.groupby("patient_id")["start_timestamp"].diff().dt.total_seconds().div(60.0))
    interval_values=hr["interval_minutes"].dropna()
    
    report.append(f"Negative intervals: {(interval_values<0).sum():,}")
    report.append(f"Zero-minute intervals: {(interval_values==0).sum():,}")
    report.append(
        f"Intervals > {LONG_GAP_MINUTES} minutes: "
        f"{(interval_values > LONG_GAP_MINUTES).sum():,}"
    )
    
    if not interval_values.empty:
        report.append("\nInterval distribution (minutes):")
        report.append(interval_values.describe(percentiles=[0.05,0.25,0.5,0.75,0.95]).to_string())
        
        positive_intervals=interval_values.loc[interval_values>0]
        if not positive_intervals.empty:
            plt.figure(figsize=(9, 5))
            plt.hist(
                positive_intervals.clip(upper=LONG_GAP_MINUTES * 4),
                bins=60,
            )
            plt.title("Heart-rate sampling intervals")
            plt.xlabel("Minutes between readings (long intervals capped)")
            plt.ylabel("Number of intervals")
            plt.tight_layout()
            plt.savefig(out_dir / "sampling_intervals.png", dpi=150)
            plt.close()
        
    #Per patient coverage
    coverage_rows=[]
    start_day=hr["start_timestamp"].min().floor("D")
    end_day=hr["start_timestamp"].max().floor("D")
    expected_days=max((end_day-start_day).days+1,1)
    
    for patient_id, group in hr.groupby("patient_id"):
        group=group.sort_values("start_timestamp")
        timestamps=group["start_timestamp"].dropna()
        gaps=group["interval_minutes"].dropna()
        
        days_observed=timestamps.dt.floor("D").nunique()
        
        coverage_rows.append({
            "patient_id": patient_id,
            "heart_rate_rows": len(group),
            "days_with_hr": days_observed,
            "expected_days_in_dataset": expected_days,
            "day_coverage_pct": safe_percentage(
                days_observed, expected_days
            ),
            "first_hr_timestamp": timestamps.min() if len(timestamps) else pd.NaT,
            "last_hr_timestamp": timestamps.max() if len(timestamps) else pd.NaT,
            "median_interval_minutes": gaps.median() if len(gaps) else np.nan,
            "p95_interval_minutes": gaps.quantile(0.95) if len(gaps) else np.nan,
            "gaps_over_60min": int((gaps > 60).sum()),
            "gaps_over_6h": int((gaps > 360).sum()),
            "max_gap_hours": gaps.max() / 60 if len(gaps) else np.nan,
        })
    
    sampling_summary=pd.DataFrame(coverage_rows).sort_values("day_coverage_pct")
    sampling_summary.to_csv(out_dir/"daily_coverage.csv",index=False)
    
    report.append("\nLowest coverage patients:")
    report.append(sampling_summary.head(10).to_string(index=False))
    
    plot_data=sampling_summary.sort_values("day_coverage_pct")
    
    plt.figure(figsize=(11,6))
    plt.barh(
        plot_data["patient_id"],
        plot_data["day_coverage_pct"],
    )
    plt.title("Heart-rate day coverage by patient")
    plt.xlabel("Percentage of days with at least one HR observation")
    plt.ylabel("Patient")
    plt.tight_layout()
    plt.savefig(out_dir / "patient_coverage.png", dpi=150)
    plt.close()

    return sampling_summary, hr

# ---------------------------------------------------------
# Daily coverage and baseline readiness
# ---------------------------------------------------------

def analyze_baseline_readiness(df, hr, out_dir, report):
    section(report,"5. RESTING DATA AVAILABILITY")
    
    usable=hr.loc[hr["data_quality"].eq("valid") & hr["hr"].between(HR_MIN_PLAUSIBLE,HR_MAX_PLAUSIBLE) & hr["activity_context"].isin(["resting", "sleeping"])].copy()
    usable["date"]=usable["start_timestamp"].dt.floor("D")
    
    daily_counts=(usable.groupby(["patient_id","date"]).size().rename("usable_resting_sleeping_observations").reset_index())
    daily_counts.to_csv(out_dir/"daily_usable_resting_counts.csv",index=False)
    
    # Days with >=10 observations are only a rough descriptive proxy.
    readiness = (daily_counts.assign(
            day_has_10_observations=lambda x:
                x["usable_resting_sleeping_observations"] >= 10
        ).groupby("patient_id")
        .agg(
            days_with_any_resting_sleeping_data=("date", "nunique"),
            days_with_10plus_observations=("day_has_10_observations", "sum"),
            total_resting_sleeping_observations=(
                "usable_resting_sleeping_observations", "sum"
            ),
            median_observations_per_observed_day=(
                "usable_resting_sleeping_observations", "median"
            ),
        ).reset_index())
    
    #Include patients with zero usable observations
    all_patients=pd.DataFrame({"patient_id": df["patient_id"].dropna().unique()})
    readiness = all_patients.merge(readiness, on="patient_id", how="left").fillna(0)
    
    readiness.to_csv(out_dir/"baseline_readiness_summary.csv",index=False)
    report.append(
        "Patients with fewer than 7 days containing >=10 observations: "
        f"{(readiness['days_with_10plus_observations'] < 7).sum()}"
    )
    report.append(
        "Patients with zero usable resting/sleeping observations: "
        f"{(readiness['total_resting_sleeping_observations'] == 0).sum()}"
    )
    report.append("\nPatient resting-data readiness:")
    report.append(readiness.sort_values("days_with_10plus_observations").head(15).to_string(index=False))
    
    return readiness

# ---------------------------------------------------------
# Diagnostic patient timelines
# ---------------------------------------------------------

def plot_patient_timelines(hr, sampling_summary,out_dir):
    timeline_dir=out_dir/"patient_timelines"
    timeline_dir.mkdir(parents=True, exist_ok=True)
    
    if hr.empty:
        return
    
    #Select patients with the lowest coverage and a few typical patients
    lowest=sampling_summary["patient_id"].head(3).tolist()
    
    median_coverage=sampling_summary["day_coverage_pct"].median()
    typical=sampling_summary.assign(
        distance=lambda x:(x["day_coverage_pct"]-median_coverage).abs()
    ).sort_values("distance")["patient_id"].head(3).tolist()
    
    selected=list(dict.fromkeys(lowest+typical))[:TIMELINE_PATIENT_COUNT]
    
    for patient_id in selected:
        group=hr.loc[hr["patient_id"].eq(patient_id)].copy()
        group=group.sort_values("start_timestamp")
        
        # Exclude impossible values from the plotted y-axis only
        plot_group=group.loc[group["hr"].between(0,240)].copy()
        if plot_group.empty:
            continue
        
        plt.figure(figsize=(13,5))
        for context,context_group in plot_group.groupby("activity_context", dropna=False):
            plt.scatter(
                context_group["start_timestamp"],
                context_group["hr"],
                label=str(context),
                alpha=0.6,
                s=8,
            )
        plt.axhline(HR_MIN_PLAUSIBLE,linestyle="--",linewidth=1)
        plt.axhline(HR_MAX_PLAUSIBLE,linestyle="--",linewidth=1)
        
        plt.title(f"Heart-rate timeline: {patient_id}")
        plt.xlabel("Timestamp (UTC)")
        plt.ylabel("Heart rate (bpm)")
        plt.legend(markerscale=2, fontsize="small", ncol=3)
        plt.tight_layout()

        filename = f"{patient_id}_timeline.png"
        plt.savefig(timeline_dir / filename, dpi=150)
        plt.close()
        
def main():
    parser = argparse.ArgumentParser(
        description="Profile synthetic health time-series data"
    )
    parser.add_argument(
        "csv_path",
        nargs="?",
        default="synthetic_health_connect_30d.csv",
        help="Path to the input CSV file",
    )
    parser.add_argument(
        "--output_dir",
        default="profiling_output",
        help="Directory for reports and plots",
    )
    args=parser.parse_args()
    
    csv_path=Path(args.csv_path)
    output_dir=Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not csv_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {csv_path}")
    
    report = [
        "SYNTHETIC HEALTH DATA - PROFILING REPORT",
        f"Input file: {csv_path.resolve()}",
        "Exploratory screening only; no clinical decisions.",
    ]
    
    df,missing_columns,extra_columns=load_data(csv_path)
    build_general_summaries(df,output_dir,report)
    hr, _=analyze_heart_rate_quality(df,output_dir,report)
    sampling_summary, hr=analyze_sampling(hr,output_dir,report)
    analyze_baseline_readiness(df, hr, output_dir, report)
    plot_patient_timelines(hr, sampling_summary, output_dir)
    
    section(report,"6. INTERPRETATION NOTES")
    report.extend([
        "1. The input CSV was not modified.",
        "2. Plausibility bounds are exploratory filters, not clinical thresholds.",
        "3. Source context and quality labels may be imperfect.",
        "4. Duplicate candidates need inspection before any deduplication.",
        "5. A day with no records is not necessarily a zero-activity day.",
        "6. Baselines and alerts were not calculated.",
        f"7. Missing expected columns: {missing_columns}",
        f"8. Additional columns: {extra_columns}",
        "",
        f"Outputs saved in: {output_dir.resolve()}",
    ])
    
    report_path=output_dir/"profiling_report.txt"
    save_text(report_path,report)
    
    print("\nProfiling complete.")
    print(f"Report: {report_path.resolve()}")
    print(f"Outputs: {output_dir.resolve()}")
    
if __name__ == "__main__":
    main()