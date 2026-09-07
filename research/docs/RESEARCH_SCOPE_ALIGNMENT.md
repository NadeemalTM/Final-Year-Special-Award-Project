# Research Scope Alignment

## Final research interpretation

The proposal's practical outcome is tea-owner earnings decision support. The deployed machine-learning target is the **next-month factory Reasonable Price (LKR/kg)**. These are aligned through a two-stage design:

1. Machine learning forecasts the selected factory's next-month Reasonable Price.
2. The decision-support layer estimates **gross tea-owner earnings** using:

   `Estimated Gross Earnings = Predicted Reasonable Price × Expected/Supplied Green Tea Leaf Quantity (kg)`

The result must be described as **gross earnings**, not net income, unless labour, fertilizer, transport, deductions, taxes and other costs are also collected and subtracted.

## Recommended wording for thesis

**Primary research outcome:** Explainable decision support for tea owners through one-month-ahead factory Reasonable Price forecasting, factory comparison and gross-earnings estimation.

**ML target:** Next-month factory Reasonable Price (LKR/kg).

**Unit of analysis:** Factory × month.

**Forecast horizon:** One month ahead.

**Decision-support outputs:**
- predicted Reasonable Price;
- approximate prediction range;
- reliability/data-quality information;
- estimated gross earnings for an entered leaf quantity;
- comparison of eligible factories by predicted Reasonable Price.

## Important limitation

The factory comparison is price-first. It does not currently model transport distance/cost, leaf-quality deductions, contracts, factory acceptance policies or other operational constraints. Therefore the UI uses “highest predicted Reasonable Price” rather than claiming an objectively “best factory”.
