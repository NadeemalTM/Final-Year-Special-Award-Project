"""Regional / district / elevation performance analysis for the held-out 2025 test set.

This script intentionally refuses to fabricate geography. It only analyzes factories whose
mapping row is marked Verified=True in research/docs/factory_region_mapping.csv.

Run:
    python research/regional_bias_analysis.py
"""
from __future__ import annotations

from pathlib import Path
import json
import math

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "research" / "results"
DOCS = ROOT / "research" / "docs"
PREDICTIONS = RESULTS / "18_test_predictions_with_residuals_intervals.csv"
MAPPING = DOCS / "factory_region_mapping.csv"
OUT = RESULTS / "regional_analysis"
FIGURES = OUT / "figures"

OUT.mkdir(parents=True, exist_ok=True)
FIGURES.mkdir(parents=True, exist_ok=True)


def as_verified(value) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "verified"}


def metric_table(df: pd.DataFrame, group_col: str) -> pd.DataFrame:
    rows = []
    overall_mae = mean_absolute_error(df["target_next_month_price"], df["predicted_price"])
    for group, part in df.groupby(group_col, dropna=False):
        part = part.dropna(subset=["target_next_month_price", "predicted_price"]).copy()
        if part.empty:
            continue
        actual = part["target_next_month_price"].astype(float)
        pred = part["predicted_price"].astype(float)
        residual = actual - pred
        mae = float(mean_absolute_error(actual, pred))
        rmse = float(math.sqrt(mean_squared_error(actual, pred)))
        nonzero = actual.abs() > 1e-12
        mape = float((np.abs((actual[nonzero] - pred[nonzero]) / actual[nonzero])).mean() * 100) if nonzero.any() else np.nan
        r2 = float(r2_score(actual, pred)) if len(part) >= 2 and actual.nunique() > 1 else np.nan
        coverage = float(part["inside_interval_90"].map(as_verified).mean() * 100) if "inside_interval_90" in part else np.nan
        rows.append(
            {
                group_col: "Unspecified" if pd.isna(group) or str(group).strip() == "" else str(group),
                "observations": int(len(part)),
                "factories": int(part["Factory"].astype(str).nunique()),
                "MAE_LKR_per_kg": mae,
                "RMSE_LKR_per_kg": rmse,
                "MAPE_pct": mape,
                "R2": r2,
                "mean_residual_LKR_per_kg": float(residual.mean()),
                "median_residual_LKR_per_kg": float(residual.median()),
                "interval_coverage_pct": coverage,
                "MAE_vs_overall_ratio": mae / overall_mae if overall_mae else np.nan,
                "small_sample_flag": bool(len(part) < 30),
            }
        )
    return pd.DataFrame(rows).sort_values("MAE_LKR_per_kg").reset_index(drop=True)


def save_bar(table: pd.DataFrame, label_col: str, value_col: str, title: str, filename: str, ylabel: str):
    if table.empty:
        return
    plot = table.sort_values(value_col, ascending=False)
    fig, ax = plt.subplots(figsize=(10, max(4, 0.45 * len(plot))))
    ax.barh(plot[label_col].astype(str), plot[value_col].astype(float))
    ax.invert_yaxis()
    ax.set_title(title)
    ax.set_xlabel(ylabel)
    fig.tight_layout()
    fig.savefig(FIGURES / filename, dpi=180, bbox_inches="tight")
    plt.close(fig)


def main():
    if not PREDICTIONS.is_file():
        raise FileNotFoundError(f"Missing held-out prediction file: {PREDICTIONS}")
    if not MAPPING.is_file():
        raise FileNotFoundError(f"Missing mapping file: {MAPPING}")

    pred = pd.read_csv(PREDICTIONS)
    mapping = pd.read_csv(MAPPING, dtype={"Factory": str})
    mapping["Verified"] = mapping["Verified"].map(as_verified)
    verified = mapping.loc[mapping["Verified"]].copy()

    eligible_test_factories = sorted(pred["Factory"].astype(str).unique())
    verified_test = verified.loc[verified["Factory"].astype(str).isin(eligible_test_factories)].copy()
    coverage_pct = len(verified_test["Factory"].unique()) / len(eligible_test_factories) * 100 if eligible_test_factories else 0

    status = {
        "held_out_test_factory_count": len(eligible_test_factories),
        "verified_test_factory_count": int(verified_test["Factory"].nunique()),
        "verified_mapping_coverage_pct": round(coverage_pct, 2),
        "analysis_status": "ready" if not verified_test.empty else "pending_verified_mapping",
        "mapping_file": str(MAPPING.relative_to(ROOT)),
        "note": "Only rows explicitly marked Verified=True are used. Missing geography is never inferred.",
    }

    if verified_test.empty:
        (OUT / "00_regional_analysis_status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
        print(json.dumps(status, indent=2))
        print("Complete research/docs/factory_region_mapping.csv with verified sources, then rerun.")
        return

    merged = pred.copy()
    merged["Factory"] = merged["Factory"].astype(str)
    keep = ["Factory", "District", "TeaGrowingRegion", "ElevationCategory", "Source", "Verified"]
    merged = merged.merge(verified_test[keep].drop_duplicates("Factory"), on="Factory", how="inner")
    merged.to_csv(OUT / "01_heldout_predictions_with_verified_geography.csv", index=False)

    overall_actual = merged["target_next_month_price"].astype(float)
    overall_pred = merged["predicted_price"].astype(float)
    overall = {
        **status,
        "analyzed_observations": int(len(merged)),
        "analyzed_factories": int(merged["Factory"].nunique()),
        "overall_MAE_LKR_per_kg": float(mean_absolute_error(overall_actual, overall_pred)),
        "overall_RMSE_LKR_per_kg": float(math.sqrt(mean_squared_error(overall_actual, overall_pred))),
        "overall_mean_residual_LKR_per_kg": float((overall_actual - overall_pred).mean()),
        "overall_interval_coverage_pct": float(merged["inside_interval_90"].map(as_verified).mean() * 100),
    }

    tables = {}
    for column, filename in [
        ("TeaGrowingRegion", "02_performance_by_tea_growing_region.csv"),
        ("District", "03_performance_by_district.csv"),
        ("ElevationCategory", "04_performance_by_elevation.csv"),
    ]:
        table = metric_table(merged.dropna(subset=[column]), column)
        table.to_csv(OUT / filename, index=False)
        tables[column] = table

    # Performance-disparity indicators: descriptive, not causal fairness claims.
    region_table = tables["TeaGrowingRegion"]
    if not region_table.empty:
        overall["max_region_MAE_ratio_vs_overall"] = float(region_table["MAE_vs_overall_ratio"].max())
        overall["max_abs_region_mean_residual_LKR_per_kg"] = float(region_table["mean_residual_LKR_per_kg"].abs().max())
        overall["region_count"] = int(len(region_table))
        overall["region_disparity_note"] = (
            "MAE ratios and mean residuals are descriptive regional performance-disparity indicators; "
            "they do not establish discrimination or causation. Small groups must be interpreted cautiously."
        )

    (OUT / "00_regional_analysis_status.json").write_text(json.dumps(overall, indent=2), encoding="utf-8")

    save_bar(region_table, "TeaGrowingRegion", "MAE_LKR_per_kg", "Held-out 2025 MAE by tea-growing region", "01_mae_by_region.png", "MAE (LKR/kg)")
    save_bar(region_table, "TeaGrowingRegion", "mean_residual_LKR_per_kg", "Mean residual by tea-growing region", "02_mean_residual_by_region.png", "Actual − predicted (LKR/kg)")
    save_bar(region_table, "TeaGrowingRegion", "interval_coverage_pct", "Approx. 90% interval coverage by region", "03_interval_coverage_by_region.png", "Coverage (%)")

    print(json.dumps(overall, indent=2))
    print(f"Regional research outputs saved to: {OUT}")


if __name__ == "__main__":
    main()
