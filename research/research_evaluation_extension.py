"""Proposal-scope completion analysis for the V2 tea Reasonable Price model.

This script does NOT retrain the deployment model. It adds research evidence requested
by the proposal/review: a 12-month seasonal-naive baseline, residual diagnostics,
monthly error analysis, and held-out coverage for the approximate 90% interval.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "research"
RESULTS = RESEARCH / "results"
FIGURES = RESULTS / "figures"
FIGURES.mkdir(parents=True, exist_ok=True)

# When this script is copied beside the complete research data package, set the path
# below or pass TEA_V2_BASE via environment if preferred.
DEFAULT_V2_BASE = ROOT / "research_data" / "colab_outputs_v2_cleaned"
V2_BASE = DEFAULT_V2_BASE

# The enhanced package includes final test predictions under research/results.
TEST_PATH = RESULTS / "09_test_2025_predictions.csv"
MASTER_PATH = V2_BASE / "master_factory_month_base_v2.csv"
METADATA_PATH = ROOT / "model_metadata.json"

if not TEST_PATH.exists():
    raise FileNotFoundError(TEST_PATH)
if not MASTER_PATH.exists():
    raise FileNotFoundError(
        f"{MASTER_PATH} not found. Copy colab_outputs_v2_cleaned into research_data/ "
        "or update V2_BASE in this script."
    )

test = pd.read_csv(TEST_PATH, parse_dates=["date", "target_date"])
master = pd.read_csv(MASTER_PATH, parse_dates=["date"])
metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
INTERVAL = float(metadata["interval_abs_q90"])


def regression_metrics(y_true, y_pred):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    smape = np.mean(2 * np.abs(y_true - y_pred) / (np.abs(y_true) + np.abs(y_pred))) * 100
    return {
        "N": int(len(y_true)),
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "RMSE": float(mean_squared_error(y_true, y_pred) ** 0.5),
        "MAPE_pct": float(np.mean(np.abs((y_true - y_pred) / y_true)) * 100),
        "sMAPE_pct": float(smape),
        "R2": float(r2_score(y_true, y_pred)),
    }


# ---------------------------------------------------------------------------
# 1) 12-month seasonal-naive baseline
# ---------------------------------------------------------------------------
seasonal_lookup = master[["Factory", "date", "reasonablePrice", "reliable_price_observation"]].copy()
seasonal_lookup["target_date"] = seasonal_lookup["date"] + pd.DateOffset(years=1)
seasonal_lookup = seasonal_lookup.rename(
    columns={
        "reasonablePrice": "seasonal_naive_price",
        "reliable_price_observation": "seasonal_source_reliable",
    }
)[["Factory", "target_date", "seasonal_naive_price", "seasonal_source_reliable"]]

extended = test.merge(seasonal_lookup, on=["Factory", "target_date"], how="left")
seasonal_reliable = extended["seasonal_source_reliable"].astype(str).str.lower().isin({"true", "1", "yes"})
seasonal_mask = extended["seasonal_naive_price"].notna() & seasonal_reliable
comparable = extended.loc[seasonal_mask].copy()

y = comparable["target_next_month_price"]
comparison_rows = []
for name, column in [
    ("CatBoost_Pct", "predicted_price"),
    ("Naive_Last_Month", "baseline_price"),
    ("Seasonal_Naive_12M", "seasonal_naive_price"),
]:
    row = {"Model": name, **regression_metrics(y, comparable[column])}
    comparison_rows.append(row)

seasonal_comparison = pd.DataFrame(comparison_rows)
seasonal_comparison.to_csv(RESULTS / "12_seasonal_naive_comparison_2025.csv", index=False)
extended.to_csv(RESULTS / "13_test_predictions_with_seasonal_naive.csv", index=False)

# ---------------------------------------------------------------------------
# 2) Residual diagnostics
# ---------------------------------------------------------------------------
test["residual"] = test["target_next_month_price"] - test["predicted_price"]
test["squared_error"] = test["residual"] ** 2
test["target_month_num"] = test["target_date"].dt.month

residual_summary = pd.DataFrame(
    [
        {
            "N": len(test),
            "MeanResidual": test["residual"].mean(),
            "MedianResidual": test["residual"].median(),
            "ResidualStd": test["residual"].std(),
            "ResidualP05": test["residual"].quantile(0.05),
            "ResidualP95": test["residual"].quantile(0.95),
            "MAE": test["absolute_error"].mean(),
            "RMSE": np.sqrt(test["squared_error"].mean()),
        }
    ]
)
residual_summary.to_csv(RESULTS / "14_residual_summary_2025.csv", index=False)

monthly = (
    test.groupby("target_month_num")
    .agg(
        N=("absolute_error", "size"),
        MAE=("absolute_error", "mean"),
        MedianAE=("absolute_error", "median"),
        RMSE=("squared_error", lambda x: float(np.sqrt(x.mean()))),
        MaxAE=("absolute_error", "max"),
        MeanResidual=("residual", "mean"),
    )
    .reset_index()
)
monthly.to_csv(RESULTS / "15_monthly_error_analysis_2025.csv", index=False)

worst = test.nlargest(20, "absolute_error")[
    [
        "Factory",
        "FactoryName",
        "target_date",
        "target_next_month_price",
        "predicted_price",
        "absolute_error",
        "ape_pct",
        "residual",
    ]
]
worst.to_csv(RESULTS / "16_top20_largest_errors_2025.csv", index=False)

# ---------------------------------------------------------------------------
# 3) Approximate 90% interval held-out coverage
# ---------------------------------------------------------------------------
test["interval_lower_90"] = np.maximum(0, test["predicted_price"] - INTERVAL)
test["interval_upper_90"] = test["predicted_price"] + INTERVAL
test["inside_interval_90"] = (
    (test["target_next_month_price"] >= test["interval_lower_90"])
    & (test["target_next_month_price"] <= test["interval_upper_90"])
)
coverage = float(test["inside_interval_90"].mean() * 100)
coverage_summary = pd.DataFrame(
    [
        {
            "NominalInterval_pct": 90.0,
            "ValidationResidualHalfWidth_LKR_per_kg": INTERVAL,
            "TestObservations": len(test),
            "CoveredObservations": int(test["inside_interval_90"].sum()),
            "HeldOutCoverage_pct": coverage,
            "Interpretation": "conservative" if coverage > 92 else ("under-covered" if coverage < 88 else "close to nominal"),
        }
    ]
)
coverage_summary.to_csv(RESULTS / "17_prediction_interval_coverage_2025.csv", index=False)
test.to_csv(RESULTS / "18_test_predictions_with_residuals_intervals.csv", index=False)

# ---------------------------------------------------------------------------
# 4) Figures
# ---------------------------------------------------------------------------
plt.figure(figsize=(8, 5))
plt.hist(test["residual"].dropna(), bins=30)
plt.axvline(0, linewidth=1)
plt.xlabel("Residual (Actual - Predicted), LKR/kg")
plt.ylabel("Frequency")
plt.title("2025 Test Residual Distribution")
plt.tight_layout()
plt.savefig(FIGURES / "residual_histogram_2025.png", dpi=180)
plt.close()

plt.figure(figsize=(8, 5))
plt.scatter(test["predicted_price"], test["residual"], s=12, alpha=0.6)
plt.axhline(0, linewidth=1)
plt.xlabel("Predicted Reasonable Price (LKR/kg)")
plt.ylabel("Residual (Actual - Predicted), LKR/kg")
plt.title("Residuals vs Predicted Price — 2025")
plt.tight_layout()
plt.savefig(FIGURES / "residual_vs_predicted_2025.png", dpi=180)
plt.close()

monthly_plot = monthly.copy()
plt.figure(figsize=(9, 5))
plt.bar(monthly_plot["target_month_num"].astype(str), monthly_plot["MAE"])
plt.xlabel("Target month")
plt.ylabel("MAE (LKR/kg)")
plt.title("Monthly Forecast MAE — 2025")
plt.tight_layout()
plt.savefig(FIGURES / "monthly_mae_2025.png", dpi=180)
plt.close()

# Actual vs predicted aggregate monthly mean keeps the figure readable across 1,002 rows.
monthly_price = test.groupby("target_date", as_index=False).agg(
    Actual=("target_next_month_price", "mean"), Predicted=("predicted_price", "mean")
)
plt.figure(figsize=(10, 5))
plt.plot(monthly_price["target_date"], monthly_price["Actual"], marker="o", label="Actual")
plt.plot(monthly_price["target_date"], monthly_price["Predicted"], marker="o", label="Predicted")
plt.xlabel("Target month")
plt.ylabel("Mean Reasonable Price (LKR/kg)")
plt.title("Mean Actual vs Predicted Reasonable Price — 2025")
plt.legend()
plt.tight_layout()
plt.savefig(FIGURES / "actual_vs_predicted_monthly_mean_2025.png", dpi=180)
plt.close()

summary = {
    "seasonal_naive_comparable_observations": int(seasonal_mask.sum()),
    "seasonal_naive_total_test_observations": int(len(test)),
    "catboost_mae_on_seasonal_comparable_subset": float(seasonal_comparison.loc[seasonal_comparison.Model == "CatBoost_Pct", "MAE"].iloc[0]),
    "seasonal_naive_mae": float(seasonal_comparison.loc[seasonal_comparison.Model == "Seasonal_Naive_12M", "MAE"].iloc[0]),
    "held_out_interval_coverage_pct": coverage,
    "residual_mean_lkr_per_kg": float(test["residual"].mean()),
    "residual_std_lkr_per_kg": float(test["residual"].std()),
}
(RESULTS / "research_extension_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(json.dumps(summary, indent=2))
