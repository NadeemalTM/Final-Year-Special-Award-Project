# Final Thesis Alignment Plan

This project is aligned to the approved proposal by treating **tea-owner earnings as the decision-support outcome** and **next-month factory Reasonable Price as the machine-learning target**.

## Core research definition

- Unit of analysis: factory × month.
- ML target: next-month factory Reasonable Price (LKR/kg).
- Owner decision-support outcome: estimated **gross** earnings = predicted Reasonable Price × expected/supplied green-leaf quantity (kg).
- Forecast horizon: one month ahead.
- The system must not call `price × kg` net income unless owner costs are also deducted.

## Proposal requirement → thesis evidence

| Proposal requirement | Final thesis section | Evidence / project artifact |
|---|---|---|
| Production, auction, export, climate, macroeconomic integration | Ch. 3 Methodology | `research/docs/Research_Data_Documentation.xlsx` |
| Data cleaning, missing data, temporal alignment, feature engineering | Ch. 3 + Ch. 5 | V2 notebook + feature dictionary |
| Linear / Random Forest / XGBoost / LSTM comparison | Ch. 5 + Ch. 6 | `research/results/original_v2/` |
| CatBoost final model | Ch. 5 + Ch. 6 | model + metadata + final test metrics |
| Time-aware train/validation/test strategy | Ch. 3 + Ch. 6 | time split results |
| Rolling validation | Ch. 3 + Ch. 6 | tuning / rolling-CV results |
| MAE, RMSE, MAPE, R² | Ch. 6 | model comparison CSVs |
| Seasonal baseline | Ch. 6 | `12_seasonal_naive_comparison_2025.csv` |
| Residual diagnostics | Ch. 6 | `14–16` result files + figures |
| Prediction uncertainty | Ch. 6 | `17_prediction_interval_coverage_2025.csv` |
| Explainable AI / SHAP | Ch. 5 + Ch. 6 | global SHAP CSV + local API SHAP |
| Region-wise error / bias analysis | Ch. 6 | run `research/regional_bias_analysis.py` after verified mapping |
| Tea-owner earnings support | Ch. 4 + Ch. 5 | `/estimate-earnings` endpoint + frontend |
| Factory selection decision support | Ch. 4 + Ch. 5 | `/compare-factories` + optional regional filters |
| DSS evaluation | Ch. 6 | real user data + `research/user_evaluation_analysis.py` |
| Ethics / privacy / responsible AI | Ch. 3 + Ch. 7 | consent process, anonymized evaluation, limitations/model card |
| Design Science Research | Ch. 3 + Ch. 7 | problem → objectives → design → development → demonstration → evaluation → communication |

## Chapter 1 — Introduction

Clarify the practical problem: tea owners need advance knowledge of likely factory Reasonable Price to estimate gross earnings and compare selling alternatives. Do not state that the ML model directly observes owner net income.

## Chapter 2 — Literature Review

Cover tea price / production forecasting, local and foreign market factors, ensemble ML, LSTM, CatBoost, explainability, uncertainty, DSS and producer decision support. Keep causal claims separate from predictive associations.

## Chapter 3 — Methodology

Document the actual implementation, including the chronological split and one-month-ahead leakage rule. If the final split differs from the proposal's approximate 70/15/15 wording, justify the calendar boundaries as a temporal-integrity decision rather than hiding the difference.

Add verified geography only from `research/docs/factory_region_mapping.csv`. Never infer missing region/elevation values.

## Chapter 4 — System Requirements and Design

Add functional requirements for:
- single-factory price forecast;
- gross-earnings estimation;
- factory comparison;
- optional district / tea-growing region / elevation filtering when mapping is verified;
- reliability and uncertainty display;
- SHAP explanation;
- anonymized research evaluation form, enabled only after the required approval process.

## Chapter 5 — Implementation

Describe FastAPI, CatBoost, feature store, React UI, earnings formula, regional metadata layer, optional research-evaluation endpoint, validation rules and security/privacy constraints.

## Chapter 6 — Testing and Evaluation

Include:
- model comparison;
- final 2025 held-out metrics;
- seasonal baseline;
- residual diagnostics;
- interval coverage;
- factory-wise evaluation;
- **regional/district/elevation evaluation after verified mapping is available**;
- **real SUS/task evaluation after genuine participants complete the study**.

Do not fabricate either regional mapping or participant results.

## Chapter 7 — Conclusions and Recommendations

Conclude on the price-forecasting engine and decision-support value. State that gross earnings are an estimate based on owner quantity and forecast price. Net earnings would require cost data. Discuss transport, distance, quality rules, contracts, factory acceptance constraints, regional weather coverage, data publication delay and market shocks as limitations/future work.

## Final evidence generation

After geography and participant data are complete, run:

```bash
python research/regional_bias_analysis.py
python research/user_evaluation_analysis.py
python research/generate_thesis_evidence.py
```

Then use `research/docs/THESIS_EVIDENCE_AUTO.md` as the final checklist when updating the dissertation.
