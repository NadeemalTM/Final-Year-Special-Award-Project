# Final Research Specification — Supervisor Review Draft

## Suggested title
**Explainable Machine Learning-Based One-Month-Ahead Tea Factory Reasonable Price Prediction for Tea Owner Earnings Estimation and Decision Support in Sri Lanka**

## Practical problem
Tea owners need advance information about the Reasonable Price likely to be paid by factories so that they can estimate expected gross earnings and compare price alternatives before making a selling/planning decision.

## Machine-learning target
Next-month factory Reasonable Price, measured in **LKR/kg**.

## Decision-support outcome
**Estimated Gross Earnings = Predicted Factory Reasonable Price × Expected/Supplied Green Tea Leaf Quantity (kg)**.

This is not net income unless production and selling costs are collected and deducted.

## Unit of analysis
One **factory × month** observation.

## Forecast horizon
One month ahead (`t` information → `t+1` Reasonable Price).

## Aim
To develop and evaluate an explainable machine-learning-based decision-support framework that forecasts one-month-ahead factory Reasonable Prices and enables tea owners to estimate gross earnings and compare factory price alternatives using production dynamics and local–international market factors.

## Research questions
1. Which historical factory, production, weather, exchange-rate, export and tea-market variables provide useful predictive information for next-month factory Reasonable Price?
2. Which forecasting approach provides the highest one-month-ahead Reasonable Price prediction accuracy?
3. How does forecasting performance vary across factories and, where verified mapping is available, tea-producing regions?
4. How can predicted Reasonable Prices and owner leaf quantity be combined to estimate gross earnings and support factory-price comparison?
5. How can explainable AI improve transparency of the forecasting and decision-support process?

## Objectives
1. Integrate historical Reasonable Price, production, climate, exchange-rate, export and international tea-market data.
2. Clean, harmonize and temporally align the data, including reliability controls for low-volume price observations.
3. Engineer leakage-safe lag, rolling, change, seasonality and trend features for one-month-ahead forecasting.
4. Develop and compare baseline, Linear/Ridge, Random Forest, XGBoost, CatBoost and LSTM approaches.
5. Evaluate performance using MAE, RMSE, MAPE, sMAPE (supplementary), R², rolling validation, residual diagnostics and prediction-interval coverage.
6. Evaluate factory-level performance and complete region-wise analysis if a verified mapping becomes available.
7. Apply SHAP-based explainability to global and local model behaviour.
8. Implement a web decision-support system for price prediction, gross-earnings estimation and factory comparison.
9. Evaluate the completed DSS with real users after any required university ethics/approval process.

## Key scope boundary
The system ranks factories by **predicted Reasonable Price** only. It does not currently include transport cost, distance, leaf-quality deductions, contractual conditions or factory acceptance policies. These must be stated as limitations or added as verified features in future work.
