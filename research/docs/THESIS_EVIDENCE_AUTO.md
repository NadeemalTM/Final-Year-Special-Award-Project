# Auto-Generated Thesis Evidence Status

> Generated from the project artifacts. Pending sections are intentionally left pending rather than filled with assumed findings.

## Proposal-to-thesis alignment

| Proposal area | Evidence status | Thesis placement |
|---|---|---|
| Multi-source acquisition and preprocessing | Available | Chapter 3 Methodology + Chapter 5 Implementation |
| Multiple model comparison | Available | Chapter 5 + Chapter 6 |
| MAE/RMSE/MAPE/R² | Available | Chapter 6 |
| Rolling / chronological validation | Available | Chapter 3 + Chapter 6 |
| Residual diagnostics | Available | Chapter 6 |
| SHAP explainability | Available | Chapter 5 + Chapter 6 |
| Gross earnings decision support (price × kg) | Available | Chapter 4 + Chapter 5 |
| Factory comparison DSS | Available | Chapter 4 + Chapter 5 |
| Region-wise evaluation | Pending verified factory geography | Chapter 6 |
| Real user / SUS evaluation | Pending real participant data | Chapter 6 |
| Ethics / responsible use | Documentation available; university process remains external | Chapter 3 + Chapter 7 |

## Final held-out technical evidence

| Model | MAE | RMSE | MAPE_pct | R2 |
|---|---|---|---|---|
| FINAL_CatBoost_Pct | 6.79143199602794 | 9.90985992888054 | 3.9911142547470577 | 0.6941287747583702 |
| FINAL_Naive_Baseline | 7.129799195608783 | 10.47151801999012 | 4.218752666181169 | 0.6584747014630633 |

## Approximate prediction interval evaluation

| NominalInterval_pct | ValidationResidualHalfWidth_LKR_per_kg | TestObservations | CoveredObservations | HeldOutCoverage_pct | Interpretation |
|---|---|---|---|---|---|
| 90.0 | 26.01646945237164 | 1002 | 978 | 97.60479041916167 | conservative |

## Regional performance / bias analysis

```json
{
  "held_out_test_factory_count": 88,
  "verified_test_factory_count": 0,
  "verified_mapping_coverage_pct": 0.0,
  "analysis_status": "pending_verified_mapping",
  "mapping_file": "research/docs/factory_region_mapping.csv",
  "note": "Only rows explicitly marked Verified=True are used. Missing geography is never inferred."
}
```

## DSS user evaluation

```json
{
  "analysis_status": "pending_real_participant_data",
  "response_count": 0,
  "note": "No participant data were fabricated. Collect real responses after applicable ethics/approval requirements."
}
```

## Terminology that must remain consistent

- ML target: next-month factory Reasonable Price (LKR/kg).
- Owner decision-support output: estimated **gross** earnings = predicted Reasonable Price × expected/supplied green-leaf kg.
- Do not call this net income unless production/transport/other costs are deducted.
- SHAP explains predictive model contributions; it does not establish causation.
- Factory ranking is price-based decision support, not an unconditional claim of the objectively best factory.