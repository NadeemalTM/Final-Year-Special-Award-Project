"""Analyze genuine DSS user-evaluation responses.

The script does not generate synthetic respondents. If no real responses exist, it writes a
pending-status file and exits. Standard SUS scoring is computed from the ten 1–5 items.

Run after real data collection:
    python research/user_evaluation_analysis.py
"""
from __future__ import annotations

from pathlib import Path
import json

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "research" / "user_evaluation" / "responses.csv"
OUT = ROOT / "research" / "results" / "user_evaluation"
FIGURES = OUT / "figures"
OUT.mkdir(parents=True, exist_ok=True)
FIGURES.mkdir(parents=True, exist_ok=True)

TASKS = [f"task{i}_success" for i in range(1, 6)]
LIKERT = [
    "price_clarity_1to5",
    "earnings_clarity_1to5",
    "uncertainty_clarity_1to5",
    "usefulness_1to5",
    "trust_appropriateness_1to5",
]
SUS = [f"sus_q{i}" for i in range(1, 11)]


def bool_value(v):
    return str(v).strip().lower() in {"1", "true", "yes", "y"}


def sus_score(row) -> float:
    adjusted = []
    for i in range(1, 11):
        value = float(row[f"sus_q{i}"])
        adjusted.append(value - 1 if i % 2 == 1 else 5 - value)
    return sum(adjusted) * 2.5


def main():
    if not DATA.is_file() or DATA.stat().st_size == 0:
        status = {
            "analysis_status": "pending_real_participant_data",
            "response_count": 0,
            "note": "No participant data were fabricated. Collect real responses after applicable ethics/approval requirements.",
        }
        (OUT / "00_user_evaluation_status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
        print(json.dumps(status, indent=2))
        return

    df = pd.read_csv(DATA)
    missing = [c for c in TASKS + LIKERT + SUS if c not in df.columns]
    if missing:
        raise ValueError(f"Evaluation response file is missing columns: {missing}")
    if df.empty:
        raise ValueError("Evaluation response file contains no responses.")

    for c in TASKS:
        df[c] = df[c].map(bool_value)
    for c in LIKERT + SUS:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["sus_score_recalculated"] = df.apply(sus_score, axis=1)
    df.to_csv(OUT / "01_scored_participant_responses.csv", index=False)

    task_summary = pd.DataFrame([
        {
            "task": c,
            "success_count": int(df[c].sum()),
            "participant_count": int(len(df)),
            "success_rate_pct": float(df[c].mean() * 100),
        }
        for c in TASKS
    ])
    task_summary.to_csv(OUT / "02_task_completion_summary.csv", index=False)

    likert_summary = pd.DataFrame([
        {
            "measure": c,
            "mean": float(df[c].mean()),
            "median": float(df[c].median()),
            "std": float(df[c].std(ddof=1)) if len(df) > 1 else 0.0,
            "n": int(df[c].notna().sum()),
        }
        for c in LIKERT
    ])
    likert_summary.to_csv(OUT / "03_likert_summary.csv", index=False)

    role_summary = (
        df.groupby("role", dropna=False)
        .agg(
            participants=("participant_code", "count"),
            mean_sus=("sus_score_recalculated", "mean"),
            mean_usefulness=("usefulness_1to5", "mean"),
            mean_trust=("trust_appropriateness_1to5", "mean"),
        )
        .reset_index()
    )
    role_summary.to_csv(OUT / "04_role_summary.csv", index=False)

    summary = {
        "analysis_status": "completed_from_real_responses",
        "response_count": int(len(df)),
        "mean_SUS": float(df["sus_score_recalculated"].mean()),
        "median_SUS": float(df["sus_score_recalculated"].median()),
        "std_SUS": float(df["sus_score_recalculated"].std(ddof=1)) if len(df) > 1 else 0.0,
        "overall_task_completion_pct": float(df[TASKS].to_numpy(dtype=float).mean() * 100),
        "mean_usefulness_1to5": float(df["usefulness_1to5"].mean()),
        "mean_trust_appropriateness_1to5": float(df["trust_appropriateness_1to5"].mean()),
        "interpretation_note": "Report these values with participant count, recruitment method, task protocol, ethics/consent process, and limitations.",
    }
    (OUT / "00_user_evaluation_status.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(task_summary["task"], task_summary["success_rate_pct"])
    ax.set_ylim(0, 100)
    ax.set_ylabel("Task completion (%)")
    ax.set_title("DSS task-completion rates")
    fig.tight_layout()
    fig.savefig(FIGURES / "01_task_completion.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.hist(df["sus_score_recalculated"].dropna(), bins=min(10, max(3, len(df))))
    ax.set_xlabel("SUS score (0–100)")
    ax.set_ylabel("Participants")
    ax.set_title("System Usability Scale score distribution")
    fig.tight_layout()
    fig.savefig(FIGURES / "02_sus_distribution.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    print(json.dumps(summary, indent=2))
    print(f"User-evaluation outputs saved to: {OUT}")


if __name__ == "__main__":
    main()
