# TeaReasonable AI

TeaReasonable AI is a FastAPI and React decision-support application for one-month-ahead Sri Lankan tea factory Reasonable Price forecasting. It serves the existing CatBoost deployment model without retraining it.

## Included functionality

- Eligible-factory discovery with each factory's latest supported prediction month
- Guarded one-month prediction API with reliability and completeness checks
- Exact CatBoost TreeSHAP feature attributions for each prediction
- Historical-price chart and macro-market context
- Session-based result persistence across page refreshes
- Printable report workflow (`Save PDF` opens the browser print dialog)
- JSON result export
- Responsive dashboard, results, and methodology pages
- Backend and frontend automated tests
- Docker Compose deployment and GitHub Actions CI

## Project layout

```text
FINAL_DEPLOYMENT/
|-- app.py
|-- model_metadata.json
|-- prediction_feature_store.csv
|-- reasonable_price_deployment_model.joblib
|-- requirements.txt
|-- requirements-dev.txt
|-- tests/
|-- frontend/
|   |-- src/
|   |-- Dockerfile
|   |-- nginx.conf
|   |-- package.json
|   `-- vite.config.js
|-- Dockerfile
|-- compose.yaml
`-- .github/workflows/ci.yml
```

The model, metadata, and feature-store files must remain beside `app.py`.

## Local development

### 1. Backend

From the project root in PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
python -m uvicorn app:app --reload
```

The API runs at <http://127.0.0.1:8000> and its interactive documentation is at <http://127.0.0.1:8000/docs>.

If PowerShell blocks activation, enable scripts only for the current terminal:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### 2. Frontend

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open <http://127.0.0.1:5173>.

For a different API address, copy `frontend/.env.example` to `frontend/.env` and update `VITE_API_BASE_URL` before starting or building Vite.

## Automated verification

Run the backend contract and model smoke tests:

```powershell
.\venv\Scripts\python.exe -m pytest
```

Run frontend behavior and persistence tests:

```powershell
cd frontend
npm test
```

Build the production frontend:

```powershell
npm run build
```

The test suites cover API validation, CORS, prediction safeguards, TreeSHAP additivity, factory/month synchronization, successful and blocked predictions, and session result restoration.

## Docker deployment

Docker Compose serves the complete application through the frontend container and proxies `/api` to FastAPI:

```powershell
docker compose up --build
```

Open <http://localhost:8080>. API documentation is available at <http://localhost:8080/api/docs>.

Stop the deployment with:

```powershell
docker compose down
```

The backend container uses one worker because the model and feature store are loaded into each worker's memory. Scale only after measuring available RAM and request volume.

## Environment configuration

Backend CORS origins are configured as comma-separated, exact origins:

```text
CORS_ORIGINS=https://forecast.example.com,https://admin.example.com
```

Do not add path segments. Trailing slashes are normalized. Authentication cookies are not used, so credentialed CORS is disabled.

`VITE_API_BASE_URL` is compiled into the frontend build. The Docker setup uses `/api` for a same-origin reverse proxy. A standalone frontend deployment must receive its public API URL at build time.

## API summary

### `GET /health`

Returns model status, version, and explainability method.

### `GET /factories`

Returns eligible factories with their latest reliable price, feature month, and supported next prediction month.

### `POST /predict`

Example request:

```json
{
  "factory": "BF0143",
  "year": 2026,
  "month": 1
}
```

The requested month must be exactly one month after an available feature row. The API blocks a request when:

- the previous-month feature row is unavailable;
- the previous Reasonable Price is missing or unreliable;
- the factory has fewer than 36 reliable months; or
- feature completeness is below 60%.

## Explainability interpretation

The API uses CatBoost's native exact TreeSHAP implementation in raw model-output space. For the percentage-change target:

- `impact_pct_points` is the authoritative feature contribution in percentage points;
- `impact_lkr` is a local fixed-anchor LKR/kg equivalent for the displayed row;
- the SHAP baseline is the model's learned expected output, not a historical average; and
- feature attributions explain model behavior and do not establish causation.

If explanation generation fails, the price forecast remains available and the response marks the explanation unavailable.

## Production checklist

- Use HTTPS at the external reverse proxy or platform load balancer.
- Set exact production `CORS_ORIGINS` when the API is called cross-origin.
- Keep the model and feature store immutable and versioned together.
- Monitor request latency, blocked predictions, and explanation failures.
- Back up model artifacts before replacing them.
- Revalidate model quality and drift before updating the feature store or model.

## Tea-owner earnings and factory-comparison extensions

This enhanced research build adds two decision-support endpoints while preserving the existing V2 CatBoost model:

### `POST /estimate-earnings`

```json
{
  "factory": "BF0143",
  "year": 2026,
  "month": 1,
  "expected_leaf_kg": 1250
}
```

The endpoint returns the standard price forecast plus estimated **gross** earnings and a gross-earnings range. Costs are not deducted.

### `POST /compare-factories`

```json
{
  "year": 2026,
  "month": 1,
  "expected_leaf_kg": 1250,
  "top_n": 10
}
```

The endpoint ranks eligible factories by predicted Reasonable Price for the same forecast month and calculates gross earnings for the common expected quantity. It deliberately does not call SHAP for every factory, keeping comparison latency lower. Open an individual factory forecast for detailed SHAP explanation.

### Research evidence

The `research/` folder includes:
- proposal-scope completion analysis;
- 12-month seasonal-naive benchmark;
- residual diagnostics;
- 2025 prediction-interval coverage;
- SHAP/model-comparison evidence;
- a 149-column data dictionary and source register workbook;
- model card;
- user-evaluation plan and templates.

`notebooks/Tea_Reasonable_Price_End_to_End_V2_Cleaned.ipynb` contains an appended final section for the new research evaluation in Google Colab.

## V3 research-completion extensions

This build adds the remaining development scaffolding for the proposal's region-wise analysis, regional performance/bias discussion, real DSS user evaluation, and final thesis alignment. It does **not** fabricate missing geography or participant responses.

### Verified factory geography

Complete:

```text
research/docs/factory_region_mapping.csv
```

Required columns are already generated for all currently eligible factories:

```text
Factory,FactoryName,District,TeaGrowingRegion,ElevationCategory,Latitude,Longitude,Source,Verified,Notes
```

Only rows with `Verified=True` are used for regional filters or research analysis.

New API endpoints:

```text
GET /regions
GET /factory/{factory}/profile
```

`POST /compare-factories` now also accepts optional:

```json
{
  "district": "...",
  "tea_growing_region": "...",
  "elevation_category": "...",
  "verified_geography_only": true
}
```

If there is no verified mapping, the API refuses geography filters rather than guessing locations.

### Regional / bias analysis

After verified mapping is available:

```powershell
python research/regional_bias_analysis.py
```

Outputs are written to:

```text
research/results/regional_analysis/
```

The analysis reports MAE, RMSE, MAPE, R², mean residual, interval coverage, sample sizes and MAE ratios by tea-growing region, district and elevation. These are descriptive performance-disparity indicators, not causal claims of discrimination.

### Real DSS user evaluation

Research collection is disabled by default.

After the required ethics/approval process is complete, set:

```text
ENABLE_EVALUATION_COLLECTION=true
```

Then restart FastAPI. The frontend **Research Evaluation** page can collect anonymized task-completion, SUS and research-specific ratings. The backend intentionally does not request name, email, phone number or account identifiers.

New endpoints:

```text
GET  /evaluation/status
POST /evaluation/submit
```

Responses are stored locally in:

```text
research/user_evaluation/responses.csv
```

Analyze genuine responses with:

```powershell
python research/user_evaluation_analysis.py
```

No synthetic participant data are generated when the response file is empty.

### Final thesis alignment

Read:

```text
research/docs/FINAL_THESIS_ALIGNMENT.md
```

After regional and user evaluation are complete, generate the final evidence checklist:

```powershell
python research/generate_thesis_evidence.py
```

This creates:

```text
research/docs/THESIS_EVIDENCE_AUTO.md
```

Pending evidence remains explicitly marked pending.
