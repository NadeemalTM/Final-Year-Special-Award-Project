# Additional Research Evaluation — Interpretation Notes

## Seasonal-naive baseline
A 12-month seasonal-naive benchmark was added to strengthen the proposal's forecasting evaluation. A reliable seasonal value was available for **974 of 1,002** held-out 2025 observations.

On this common subset:

| Model | MAE | RMSE | MAPE | sMAPE | R² |
|---|---:|---:|---:|---:|---:|
| CatBoost_Pct | 6.6918 | 9.7752 | 3.9144% | 3.9600% | 0.6859 |
| Last-month naive | 7.0215 | 10.2663 | 4.1328% | 4.1428% | 0.6535 |
| 12-month seasonal naive | 14.4612 | 18.5570 | 8.4143% | 8.1230% | -0.1321 |

The selected CatBoost model outperformed both baselines on this comparable subset.

## Residual diagnostics
For all 1,002 final 2025 predictions:
- mean residual (Actual − Predicted): **+2.0183 LKR/kg**;
- median residual: **+1.7327 LKR/kg**;
- residual standard deviation: **9.7070 LKR/kg**.

A positive mean residual indicates a small average tendency to underpredict actual prices on the held-out period. The residual plots and largest-error table should be discussed in the final thesis rather than relying only on aggregate metrics.

## Month-wise difficulty
The highest average absolute errors in the 2025 test set occurred in:
- August: **9.92 LKR/kg** MAE;
- March: **8.28 LKR/kg** MAE;
- July: **8.18 LKR/kg** MAE.

Lower average errors included April (~4.82), February (~4.97), and May (~5.14 LKR/kg). This supports discussion of seasonal variability in forecasting difficulty.

## Approximate 90% interval
The existing interval uses a fixed empirical half-width from validation residuals. On the untouched 2025 test set it achieved **97.60% coverage (978/1,002)**, which is higher than the nominal 90%. The interval is therefore conservative on this test period and may be recalibrated in future work if narrower decision-support ranges are desired.
