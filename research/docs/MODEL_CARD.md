# Model Card — Tea Reasonable Price V2

## Intended use
One-month-ahead factory-level Reasonable Price forecasting in Sri Lanka, supporting tea-owner gross-earnings estimation and factory price comparison.

## Model
- Selected model: **CatBoost_Pct**
- Target mode: next-month percentage price change, reconstructed to LKR/kg
- Feature columns: 133
- Minimum reliable history: 36 months
- Minimum feature completeness: 60%
- Low-volume reliability threshold: 100 kg

## Data period and evaluation design
- Historical modeling data: 2015–2025
- Training: 2015–2022
- Validation/model selection: 2023–2024
- Final untouched test: 2025
- Rolling/expanding chronological folds were used during tuning.

## Final 2025 performance
- MAE: **6.7914 LKR/kg**
- RMSE: **9.9099 LKR/kg**
- MAPE: **3.9911%**
- R²: **0.6941**
- Last-month naive MAE: **7.1298 LKR/kg**
- MAE improvement vs last-month naive: **~4.75%**

## Additional proposal-scope evaluation
On the 974 held-out observations where a reliable 12-month prior price exists:
- CatBoost MAE: **6.6918 LKR/kg**
- Last-month naive MAE: **7.0215 LKR/kg**
- 12-month seasonal-naive MAE: **14.4612 LKR/kg**

The empirical interval half-width stored in metadata is **26.0165 LKR/kg**. On the 1,002 final 2025 test observations, the approximate 90% interval covered **97.60%** of actual prices. This means the interval is **conservative/wide** on the held-out test set; it does not mean the point prediction is 97.60% accurate.

## Explainability
CatBoost TreeSHAP is used for local prediction explanations, and a global SHAP importance table is stored in the research results. SHAP explains model contribution/association, not causal effects.

## Known limitations
- Weather data is currently a Ratnapura regional proxy unless a verified factory-location/weather mapping is added.
- Region-wise evaluation cannot be completed without a verified factory → district/region/elevation mapping.
- External-data publication delays must be documented so that live predictions never use information unavailable at forecast time.
- Sudden market, climate or geopolitical shocks can move prices outside the historical pattern.
- Gross earnings are calculated from predicted price × user-provided leaf quantity. Costs are not deducted.

## Non-intended use
- Guaranteed payment or investment advice
- Net-income estimation without cost data
- Arbitrary multi-month forecasting beyond the supported one-month horizon
- Declaring a factory “best” without considering non-price operational factors
