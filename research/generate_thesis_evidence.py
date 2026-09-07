"""Generate a thesis-alignment evidence report from completed research artifacts.

This file does not invent missing regional or user-evaluation findings. It reports them as
pending until the corresponding verified inputs/results exist.
"""
from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "research" / "results"
DOCS = ROOT / "research" / "docs"
OUT = DOCS / "THESIS_EVIDENCE_AUTO.md"


def load_json(path: Path):
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def df_to_markdown(df: pd.DataFrame) -> str:
    if df is None or df.empty:
        return "No rows available."
    columns = [str(c) for c in df.columns]
    rows = ["| " + " | ".join(columns) + " |", "|" + "|".join(["---"] * len(columns)) + "|"]
    for _, row in df.iterrows():
        vals = [str(row[c]).replace("|", "\\|") for c in df.columns]
        rows.append("| " + " | ".join(vals) + " |")
    return "\n".join(rows)


def main():
    regional = load_json(RESULTS / "regional_analysis" / "00_regional_analysis_status.json")
    usability = load_json(RESULTS / "user_evaluation" / "00_user_evaluation_status.json")
    interval = pd.read_csv(RESULTS / "17_prediction_interval_coverage_2025.csv") if (RESULTS / "17_prediction_interval_coverage_2025.csv").is_file() else None
    final_metrics = pd.read_csv(RESULTS / "08_final_2025_test_metrics.csv") if (RESULTS / "08_final_2025_test_metrics.csv").is_file() else None

    lines = [
        "# Auto-Generated Thesis Evidence Status",
        "",
        "> Generated from the project artifacts. Pending sections are intentionally left pending rather than filled with assumed findings.",
        "",
        "## Proposal-to-thesis alignment",
        "",
        "| Proposal area | Evidence status | Thesis placement |",
        "|---|---|---|",
        "| Multi-source acquisition and preprocessing | Available | Chapter 3 Methodology + Chapter 5 Implementation |",
        "| Multiple model comparison | Available | Chapter 5 + Chapter 6 |",
        "| MAE/RMSE/MAPE/R² | Available | Chapter 6 |",
        "| Rolling / chronological validation | Available | Chapter 3 + Chapter 6 |",
        "| Residual diagnostics | Available | Chapter 6 |",
        "| SHAP explainability | Available | Chapter 5 + Chapter 6 |",
        "| Gross earnings decision support (price × kg) | Available | Chapter 4 + Chapter 5 |",
        "| Factory comparison DSS | Available | Chapter 4 + Chapter 5 |",
        f"| Region-wise evaluation | {'Available' if regional and regional.get('analysis_status') == 'ready' else 'Pending verified factory geography'} | Chapter 6 |",
        f"| Real user / SUS evaluation | {'Available' if usability and usability.get('analysis_status') == 'completed_from_real_responses' else 'Pending real participant data'} | Chapter 6 |",
        "| Ethics / responsible use | Documentation available; university process remains external | Chapter 3 + Chapter 7 |",
        "",
        "## Final held-out technical evidence",
        "",
    ]
    if final_metrics is not None:
        lines.append(df_to_markdown(final_metrics))
    else:
        lines.append("Final metrics file not found.")
    lines += ["", "## Approximate prediction interval evaluation", ""]
    if interval is not None:
        lines.append(df_to_markdown(interval))
    else:
        lines.append("Interval-coverage result not found.")

    lines += ["", "## Regional performance / bias analysis", ""]
    if regional:
        lines.append("```json")
        lines.append(json.dumps(regional, indent=2))
        lines.append("```")
    else:
        lines.append("Pending. Complete `research/docs/factory_region_mapping.csv`, mark verified mappings, then run `python research/regional_bias_analysis.py`.")

    lines += ["", "## DSS user evaluation", ""]
    if usability:
        lines.append("```json")
        lines.append(json.dumps(usability, indent=2))
        lines.append("```")
    else:
        lines.append("Pending. Enable collection only after required ethics/approval, collect genuine responses, then run `python research/user_evaluation_analysis.py`.")

    lines += [
        "",
        "## Terminology that must remain consistent",
        "",
        "- ML target: next-month factory Reasonable Price (LKR/kg).",
        "- Owner decision-support output: estimated **gross** earnings = predicted Reasonable Price × expected/supplied green-leaf kg.",
        "- Do not call this net income unless production/transport/other costs are deducted.",
        "- SHAP explains predictive model contributions; it does not establish causation.",
        "- Factory ranking is price-based decision support, not an unconditional claim of the objectively best factory.",
    ]
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
