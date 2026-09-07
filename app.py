from pathlib import Path
import csv
import json
import logging
import os
import re
import threading
import uuid
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
from catboost import Pool
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "reasonable_price_deployment_model.joblib"
METADATA_PATH = BASE_DIR / "model_metadata.json"
FEATURE_STORE_PATH = BASE_DIR / "prediction_feature_store.csv"
REGION_MAPPING_PATH = BASE_DIR / "research" / "docs" / "factory_region_mapping.csv"
EVALUATION_DATA_PATH = BASE_DIR / "research" / "user_evaluation" / "responses.csv"
EVALUATION_ENABLED = os.getenv("ENABLE_EVALUATION_COLLECTION", "false").strip().lower() in {"1", "true", "yes"}
EVALUATION_LOCK = threading.Lock()


def require_file(path: Path, description: str) -> None:
    if not path.is_file():
        raise RuntimeError(
            f"{description} is missing. Expected it in the same directory as app.py: {path}"
        )


require_file(MODEL_PATH, "Model file")
require_file(METADATA_PATH, "Metadata file")
require_file(FEATURE_STORE_PATH, "Feature store CSV")

try:
    model = joblib.load(MODEL_PATH)
except Exception as exc:
    raise RuntimeError(
        f"Model could not be loaded from {MODEL_PATH}. "
        "Install the packages in requirements.txt and confirm that the model file is valid. "
        f"Original error: {exc}"
    ) from exc

try:
    with METADATA_PATH.open("r", encoding="utf-8") as f:
        metadata = json.load(f)
except Exception as exc:
    raise RuntimeError(
        f"Metadata could not be loaded from {METADATA_PATH}. Original error: {exc}"
    ) from exc

try:
    features = pd.read_csv(
        FEATURE_STORE_PATH,
        parse_dates=["date", "target_date"],
    )
except Exception as exc:
    raise RuntimeError(
        f"Feature store CSV could not be loaded from {FEATURE_STORE_PATH}. "
        f"Original error: {exc}"
    ) from exc

def _empty_geography_frame():
    return pd.DataFrame(
        columns=[
            "Factory",
            "FactoryName",
            "District",
            "TeaGrowingRegion",
            "ElevationCategory",
            "Latitude",
            "Longitude",
            "Source",
            "Verified",
            "Notes",
        ]
    )


def _load_geography_mapping() -> pd.DataFrame:
    if not REGION_MAPPING_PATH.is_file():
        return _empty_geography_frame()
    try:
        mapping = pd.read_csv(REGION_MAPPING_PATH, dtype={"Factory": str})
    except Exception as exc:
        logging.getLogger(__name__).warning("Could not read geography mapping: %s", exc)
        return _empty_geography_frame()
    for column in _empty_geography_frame().columns:
        if column not in mapping.columns:
            mapping[column] = np.nan
    mapping["Factory"] = mapping["Factory"].astype(str).str.strip()
    mapping["Verified"] = mapping["Verified"].map(
        lambda value: str(value).strip().lower() in {"1", "true", "yes", "verified"}
    )
    return mapping.drop_duplicates("Factory", keep="last")


geography = _load_geography_mapping()


def geography_record(factory: str) -> dict:
    if geography.empty:
        return {
            "district": None,
            "tea_growing_region": None,
            "elevation_category": None,
            "latitude": None,
            "longitude": None,
            "geography_verified": False,
        }
    row = geography.loc[geography["Factory"].astype(str) == str(factory)]
    if row.empty:
        return {
            "district": None,
            "tea_growing_region": None,
            "elevation_category": None,
            "latitude": None,
            "longitude": None,
            "geography_verified": False,
        }
    item = row.iloc[0]
    def clean_text(column):
        value = item.get(column)
        return None if pd.isna(value) or str(value).strip() == "" else str(value).strip()
    def clean_float(column):
        value = item.get(column)
        return None if pd.isna(value) else float(value)
    return {
        "district": clean_text("District"),
        "tea_growing_region": clean_text("TeaGrowingRegion"),
        "elevation_category": clean_text("ElevationCategory"),
        "latitude": clean_float("Latitude"),
        "longitude": clean_float("Longitude"),
        "geography_verified": bool(item.get("Verified", False)),
    }

FEATURE_COLS = metadata["feature_columns"]
CATEGORICAL_COLS = metadata.get("categorical_columns", ["Factory"])
MODEL_NAME = metadata["model_name"]
MODEL_VERSION = metadata.get("version", "unknown")
TARGET_MODE = metadata["target_mode"]
INTERVAL = float(metadata.get("interval_abs_q90", 0.0))
MIN_RELIABLE_MONTHS = int(metadata.get("min_reliable_months", 36))
MIN_FEATURE_COMPLETENESS = float(metadata.get("min_feature_completeness", 0.60))

if getattr(model, "feature_names_", None) and list(model.feature_names_) != FEATURE_COLS:
    raise RuntimeError("Model feature order does not match model_metadata.json.")

logger = logging.getLogger(__name__)

DEFAULT_CORS_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)
CORS_ORIGINS = tuple(
    origin.strip().rstrip("/")
    for origin in os.getenv("CORS_ORIGINS", ",".join(DEFAULT_CORS_ORIGINS)).split(",")
    if origin.strip()
)

app = FastAPI(title="Tea Reasonable Price Prediction API — V2", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(CORS_ORIGINS),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PredictionRequest(BaseModel):
    factory: str = Field(..., examples=["BF0143"])
    year: int = Field(..., ge=2015, le=2100)
    month: int = Field(..., ge=1, le=12)


def as_bool(v):
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    return str(v).strip().lower() in {"true", "1", "yes"}


def reconstruct(raw, base, mode):
    if mode == "direct":
        return raw
    if mode == "delta":
        return base + raw
    if mode == "pct":
        return base * (1.0 + raw)
    raise ValueError(mode)


FEATURE_LABELS = {
    "Factory": "Factory profile",
    "reasonablePrice": "Previous reasonable price",
    "NetAvg": "Net auction average",
    "GrossAvg": "Gross auction average",
    "NetQtySold": "Net quantity sold",
    "GrossQtySold": "Gross quantity sold",
    "TotalProduction": "Tea production",
    "price_change_1": "Previous-month price momentum",
    "price_pct_change_1": "Previous-month price change",
    "production_change_1": "Production momentum",
    "avg_temperature": "Average temperature",
    "avg_humidity": "Average humidity",
    "total_rainfall": "Rainfall",
    "usd_lkr": "USD/LKR exchange rate",
    "export_quantity_kg": "Tea export volume",
    "export_value_usd": "Tea export value",
    "world_tea_average_usd_per_kg": "World tea average",
    "tea_colombo_usd_per_kg": "Colombo tea price",
    "competitor_tea_average_usd_per_kg": "Competitor tea average",
    "colombo_premium_vs_competitors_pct": "Colombo market premium",
    "target_month": "Forecast seasonality",
    "target_month_sin": "Seasonal cycle",
    "target_month_cos": "Seasonal cycle",
    "trend_month_index": "Long-term market trend",
}


def feature_label(feature_name: str) -> str:
    if feature_name in FEATURE_LABELS:
        return FEATURE_LABELS[feature_name]
    lag_match = re.match(r"(.+)_lag_(\d+)$", feature_name)
    if lag_match:
        base_name, months = lag_match.groups()
        base_label = FEATURE_LABELS.get(
            base_name, base_name.replace("_", " ").title()
        )
        return f"{base_label} ({months}-month lag)"
    return feature_name.replace("_", " ").title()


def price_impact(shap_value: float, current_price: float) -> float:
    if TARGET_MODE == "pct":
        return shap_value * current_price
    return shap_value


def explain_prediction(
    prediction_pool: Pool, current_price: float, predicted_raw: float
) -> dict:
    """Return local CatBoost SHAP attributions in the displayed LKR/kg scale."""
    if not hasattr(model, "get_feature_importance"):
        return {
            "available": False,
            "method": None,
            "positive_drivers": [],
            "negative_drivers": [],
        }

    shap_values = model.get_feature_importance(
        prediction_pool,
        type="ShapValues",
        shap_calc_type="Exact",
        model_output="Raw",
        thread_count=1,
    )[0]
    feature_values = shap_values[:-1]
    base_value = float(shap_values[-1])
    if not np.isclose(
        base_value + float(np.sum(feature_values)),
        predicted_raw,
        rtol=1e-7,
        atol=1e-9,
    ):
        raise RuntimeError("SHAP contributions do not add up to the model output.")
    drivers = []
    for feature_name, shap_value in zip(FEATURE_COLS, feature_values):
        impact = float(price_impact(float(shap_value), current_price))
        drivers.append(
            {
                "feature": feature_name,
                "label": feature_label(feature_name),
                "impact_pct_points": round(float(shap_value) * 100, 3),
                "impact_lkr": round(impact, 2),
            }
        )

    feature_contributions = sorted(
        drivers,
        key=lambda item: abs(item["impact_pct_points"]),
        reverse=True,
    )
    positive = sorted(
        (item for item in feature_contributions if item["impact_pct_points"] > 0),
        key=lambda item: item["impact_lkr"],
        reverse=True,
    )[:4]
    negative = sorted(
        (item for item in feature_contributions if item["impact_pct_points"] < 0),
        key=lambda item: item["impact_lkr"],
    )[:4]
    baseline_price = reconstruct(base_value, current_price, TARGET_MODE)
    return {
        "available": True,
        "method": "CatBoost TreeSHAP (exact)",
        "explained_output": "one_month_price_change",
        "predicted_change_pct": round(predicted_raw * 100, 4),
        "baseline_price": round(float(baseline_price), 2),
        "baseline_change_pct": round(base_value * 100, 4),
        "feature_contributions": feature_contributions,
        "positive_drivers": positive,
        "negative_drivers": negative,
        "note": (
            "SHAP values explain this model output relative to its learned baseline. "
            "They are associations, not proof of causation."
        ),
    }


@app.get("/health")
def health():
    verified_geography = int(geography["Verified"].sum()) if not geography.empty else 0
    return {
        "status": "ok",
        "model": MODEL_NAME,
        "version": MODEL_VERSION,
        "explainability": "CatBoost TreeSHAP (exact)",
        "verified_geography_factories": verified_geography,
        "evaluation_collection_enabled": EVALUATION_ENABLED,
    }


@app.get("/regions")
def regions_list():
    """Report verified mapping coverage and available research geography filters."""
    eligible_factories = set(
        features.loc[features["eligible_factory"].map(as_bool), "Factory"].astype(str).unique()
    )
    mapping = geography.copy()
    if mapping.empty:
        return {
            "status": "pending_mapping",
            "eligible_factory_count": len(eligible_factories),
            "mapped_factory_count": 0,
            "verified_factory_count": 0,
            "coverage_pct": 0.0,
            "districts": [],
            "tea_growing_regions": [],
            "elevation_categories": [],
        }
    mapping = mapping.loc[mapping["Factory"].astype(str).isin(eligible_factories)].copy()
    verified = mapping.loc[mapping["Verified"]].copy()
    def values(column):
        if column not in verified:
            return []
        return sorted(
            str(value).strip()
            for value in verified[column].dropna().unique()
            if str(value).strip()
        )
    verified_count = int(verified["Factory"].nunique())
    coverage = (verified_count / len(eligible_factories) * 100.0) if eligible_factories else 0.0
    return {
        "status": "ready" if verified_count else "pending_mapping",
        "eligible_factory_count": len(eligible_factories),
        "mapped_factory_count": int(mapping["Factory"].nunique()),
        "verified_factory_count": verified_count,
        "coverage_pct": round(coverage, 1),
        "districts": values("District"),
        "tea_growing_regions": values("TeaGrowingRegion"),
        "elevation_categories": values("ElevationCategory"),
    }


@app.get("/factories")
def factories_list():
    eligible = features.loc[features["eligible_factory"].map(as_bool)].copy()
    latest = (
        eligible.loc[eligible["reasonablePrice"].notna()]
        .sort_values("date")
        .groupby("Factory", as_index=False)
        .tail(1)
    )
    fac = latest[
        ["Factory", "FactoryName", "reasonablePrice", "date", "target_date"]
    ].sort_values("Factory")
    fac = fac.rename(
        columns={
            "reasonablePrice": "latest_reasonable_price",
            "date": "latest_data_month",
            "target_date": "latest_prediction_month",
        }
    )
    fac["latest_data_month"] = fac["latest_data_month"].dt.strftime("%Y-%m-%d")
    fac["latest_prediction_month"] = fac["latest_prediction_month"].dt.strftime(
        "%Y-%m-%d"
    )
    records = fac.to_dict(orient="records")
    for item in records:
        item.update(geography_record(item["Factory"]))
    return records


@app.get("/factory/{factory}/profile")
def factory_profile(factory: str):
    rows = features.loc[features["Factory"].astype(str) == str(factory)].sort_values("date")
    if rows.empty:
        raise HTTPException(status_code=404, detail="Factory not found.")
    latest = rows.iloc[-1]
    reliable = rows["reasonablePrice"].notna() & rows["reliable_price_observation"].map(as_bool)
    profile = {
        "factory": str(factory),
        "factory_name": str(latest.get("FactoryName", factory)),
        "available_months": int(len(rows)),
        "reliable_price_months": int(reliable.sum()),
        "latest_data_month": str(pd.Timestamp(latest["date"]).date()),
    }
    profile.update(geography_record(factory))
    return profile


@app.post("/predict")
def predict(req: PredictionRequest):
    target_date = pd.Timestamp(year=req.year, month=req.month, day=1)
    feature_date = target_date - pd.offsets.MonthBegin(1)
    fstr = str(req.factory)
    row = features[
        (features["Factory"].astype(str) == fstr)
        & (features["date"] == feature_date)
    ].copy()
    if row.empty:
        raise HTTPException(
            status_code=400,
            detail=(
                "No previous-month feature row. Only one-month-ahead prediction "
                "from available history is supported."
            ),
        )
    if "target_date" in row and not (row["target_date"] == target_date).all():
        raise HTTPException(
            status_code=400,
            detail="Feature row is not configured for the requested next month.",
        )
    if not as_bool(row["eligible_factory"].iloc[0]):
        raise HTTPException(
            status_code=400,
            detail="Factory does not meet minimum reliable-history requirement.",
        )
    if pd.isna(row["reasonablePrice"].iloc[0]) or not as_bool(
        row["reliable_price_observation"].iloc[0]
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Previous-month Reasonable Price is missing or flagged unreliable; "
                "prediction blocked."
            ),
        )

    history_rows = features[
        (features["Factory"].astype(str) == fstr)
        & (features["date"] <= feature_date)
    ]
    history = int(
        (
            history_rows["reasonablePrice"].notna()
            & history_rows["reliable_price_observation"].map(as_bool)
        ).sum()
    )
    if history < MIN_RELIABLE_MONTHS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Only {history} reliable history months; "
                f"need {MIN_RELIABLE_MONTHS}."
            ),
        )
    completeness = float(row[FEATURE_COLS].notna().mean(axis=1).iloc[0])
    if completeness < MIN_FEATURE_COMPLETENESS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Feature completeness {completeness * 100:.1f}% is below "
                f"the minimum of {MIN_FEATURE_COMPLETENESS * 100:.1f}%."
            ),
        )

    X = row[FEATURE_COLS].copy()
    if "CatBoost" in MODEL_NAME:
        X["Factory"] = X["Factory"].fillna("UNKNOWN").astype(str)
    prediction_pool = Pool(
        data=X,
        cat_features=CATEGORICAL_COLS,
        feature_names=FEATURE_COLS,
    )
    raw = float(model.predict(prediction_pool)[0])
    current = float(row["reasonablePrice"].iloc[0])
    predicted = float(reconstruct(raw, current, TARGET_MODE))
    try:
        explanation = explain_prediction(prediction_pool, current, raw)
    except Exception:
        logger.exception("Could not compute local prediction explanation")
        explanation = {
            "available": False,
            "method": None,
            "positive_drivers": [],
            "negative_drivers": [],
            "note": "Local feature attribution is unavailable for this prediction.",
        }
    production_available = (
        bool(row["TotalProduction"].notna().iloc[0])
        if "TotalProduction" in row
        else False
    )
    reliability = (
        "HIGH"
        if completeness >= 0.90 and production_available and history >= 60
        else ("MEDIUM" if completeness >= 0.75 else "LOW")
    )
    warnings = []
    if not production_available:
        warnings.append(
            "Current-month TC5 production is missing; model imputation is used."
        )
    if completeness < 0.80:
        warnings.append("Moderate feature completeness.")

    history_points = (
        history_rows.loc[
            history_rows["reasonablePrice"].notna()
            & history_rows["reliable_price_observation"].map(as_bool),
            ["date", "reasonablePrice"],
        ]
        .sort_values("date")
        .tail(18)
    )
    price_history = [
        {"month": str(item.date.date()), "price": round(float(item.reasonablePrice), 2)}
        for item in history_points.itertuples(index=False)
    ]

    def optional_number(column):
        if column not in row or pd.isna(row[column].iloc[0]):
            return None
        return round(float(row[column].iloc[0]), 2)

    geography_info = geography_record(fstr)
    return {
        "factory": fstr,
        "factory_name": str(row["FactoryName"].iloc[0]),
        **geography_info,
        "feature_month": str(feature_date.date()),
        "prediction_month": str(target_date.date()),
        "current_reasonable_price": current,
        "predicted_reasonable_price": predicted,
        "approx_lower_90": max(0.0, predicted - INTERVAL),
        "approx_upper_90": predicted + INTERVAL,
        "model": MODEL_NAME,
        "target_mode": TARGET_MODE,
        "reliability": reliability,
        "feature_completeness_pct": round(completeness * 100, 1),
        "reliable_history_months": history,
        "production_available": production_available,
        "warnings": warnings,
        "price_history": price_history,
        "market_context": {
            "colombo_tea_usd_per_kg": optional_number("tea_colombo_usd_per_kg"),
            "world_tea_usd_per_kg": optional_number("world_tea_average_usd_per_kg"),
            "usd_lkr": optional_number("usd_lkr"),
            "rainfall_mm": optional_number("total_rainfall"),
        },
        "explanation": explanation,
    }


# ---------------------------------------------------------------------------
# Tea-owner decision-support extensions
# ---------------------------------------------------------------------------
class EarningsRequest(PredictionRequest):
    expected_leaf_kg: float = Field(..., gt=0, le=10_000_000, examples=[1250])


class FactoryComparisonRequest(BaseModel):
    year: int = Field(..., ge=2015, le=2100)
    month: int = Field(..., ge=1, le=12)
    expected_leaf_kg: float = Field(..., gt=0, le=10_000_000, examples=[1250])
    top_n: int = Field(10, ge=1, le=104)
    district: str | None = None
    tea_growing_region: str | None = None
    elevation_category: str | None = None
    verified_geography_only: bool = False


def _earnings_fields(price_payload: dict, expected_leaf_kg: float) -> dict:
    """Convert a price forecast into gross-earnings decision-support values."""
    quantity = float(expected_leaf_kg)
    price = float(price_payload["predicted_reasonable_price"])
    lower_price = float(price_payload["approx_lower_90"])
    upper_price = float(price_payload["approx_upper_90"])
    return {
        "expected_leaf_kg": quantity,
        "estimated_gross_earnings_lkr": price * quantity,
        "gross_earnings_lower_90_lkr": lower_price * quantity,
        "gross_earnings_upper_90_lkr": upper_price * quantity,
        "earnings_formula": "predicted_reasonable_price_lkr_per_kg × expected_leaf_kg",
        "earnings_type": "gross",
        "earnings_note": (
            "This is an estimated gross earnings value. Labour, fertilizer, transport, "
            "quality deductions, taxes, contractual terms and other costs are not deducted."
        ),
    }


@app.post("/estimate-earnings")
def estimate_earnings(req: EarningsRequest):
    """Forecast one factory's price and estimate gross tea-owner earnings."""
    price_payload = predict(
        PredictionRequest(factory=req.factory, year=req.year, month=req.month)
    )
    return {**price_payload, **_earnings_fields(price_payload, req.expected_leaf_kg)}


@app.post("/compare-factories")
def compare_factories(req: FactoryComparisonRequest):
    """
    Rank currently eligible factories by the same one-month-ahead Reasonable Price
    model and translate each price into gross earnings for a common leaf quantity.

    This endpoint intentionally does not call the local SHAP routine for every factory;
    explanations remain available through /predict or /estimate-earnings for a selected
    factory.
    """
    target_date = pd.Timestamp(year=req.year, month=req.month, day=1)
    feature_date = target_date - pd.offsets.MonthBegin(1)

    rows = features.loc[features["date"] == feature_date].copy()
    if rows.empty:
        raise HTTPException(
            status_code=400,
            detail=(
                "No previous-month feature rows are available for this forecast month. "
                "Only one-month-ahead comparison from available history is supported."
            ),
        )

    rows = rows.loc[rows["eligible_factory"].map(as_bool)].copy()
    rows = rows.loc[
        rows["reasonablePrice"].notna()
        & rows["reliable_price_observation"].map(as_bool)
    ].copy()

    geography_filters_requested = any(
        [req.district, req.tea_growing_region, req.elevation_category, req.verified_geography_only]
    )
    if geography_filters_requested:
        verified_mapping = geography.loc[geography["Verified"]].copy() if not geography.empty else geography
        if verified_mapping.empty:
            raise HTTPException(
                status_code=400,
                detail=(
                    "No verified factory geography mapping is available. Complete "
                    "research/docs/factory_region_mapping.csv before using regional filters."
                ),
            )
        merge_cols = ["Factory", "District", "TeaGrowingRegion", "ElevationCategory", "Verified"]
        rows["Factory"] = rows["Factory"].astype(str)
        verified_mapping["Factory"] = verified_mapping["Factory"].astype(str)
        rows = rows.merge(verified_mapping[merge_cols], on="Factory", how="inner")
        if req.district:
            rows = rows.loc[rows["District"].astype(str).str.casefold() == req.district.strip().casefold()]
        if req.tea_growing_region:
            rows = rows.loc[rows["TeaGrowingRegion"].astype(str).str.casefold() == req.tea_growing_region.strip().casefold()]
        if req.elevation_category:
            rows = rows.loc[rows["ElevationCategory"].astype(str).str.casefold() == req.elevation_category.strip().casefold()]
        if rows.empty:
            raise HTTPException(status_code=400, detail="No factories match the requested verified geography filters.")

    reliable_history_mask = (
        features["reasonablePrice"].notna()
        & features["reliable_price_observation"].map(as_bool)
        & (features["date"] <= feature_date)
    )
    history_counts = (
        features.loc[reliable_history_mask]
        .groupby(features.loc[reliable_history_mask, "Factory"].astype(str))
        .size()
    )
    rows["_history"] = rows["Factory"].astype(str).map(history_counts).fillna(0).astype(int)
    rows["_completeness"] = rows[FEATURE_COLS].notna().mean(axis=1)
    rows = rows.loc[
        (rows["_history"] >= MIN_RELIABLE_MONTHS)
        & (rows["_completeness"] >= MIN_FEATURE_COMPLETENESS)
    ].copy()

    if rows.empty:
        raise HTTPException(
            status_code=400,
            detail="No factories pass the reliability checks for the requested forecast month.",
        )

    X = rows[FEATURE_COLS].copy()
    if "CatBoost" in MODEL_NAME and "Factory" in X:
        X["Factory"] = X["Factory"].fillna("UNKNOWN").astype(str)
    pool = Pool(data=X, cat_features=CATEGORICAL_COLS, feature_names=FEATURE_COLS)
    raw_predictions = np.asarray(model.predict(pool), dtype=float)
    current_prices = rows["reasonablePrice"].astype(float).to_numpy()

    if TARGET_MODE == "direct":
        predicted_prices = raw_predictions
    elif TARGET_MODE == "delta":
        predicted_prices = current_prices + raw_predictions
    elif TARGET_MODE == "pct":
        predicted_prices = current_prices * (1.0 + raw_predictions)
    else:
        raise HTTPException(status_code=500, detail=f"Unsupported target mode: {TARGET_MODE}")

    quantity = float(req.expected_leaf_kg)
    results = []
    rows = rows.reset_index(drop=True)
    for idx, predicted in enumerate(predicted_prices):
        row_item = rows.iloc[idx]
        predicted = float(predicted)
        current = float(row_item["reasonablePrice"])
        completeness = float(row_item["_completeness"])
        history = int(row_item["_history"])
        production_available = not pd.isna(row_item.get("TotalProduction", np.nan))
        reliability = (
            "HIGH"
            if completeness >= 0.90 and production_available and history >= 60
            else ("MEDIUM" if completeness >= 0.75 else "LOW")
        )
        lower = max(0.0, predicted - INTERVAL)
        upper = predicted + INTERVAL
        geo = geography_record(str(row_item["Factory"]))
        results.append(
            {
                "factory": str(row_item["Factory"]),
                "factory_name": str(row_item["FactoryName"]),
                **geo,
                "current_reasonable_price": current,
                "predicted_reasonable_price": predicted,
                "predicted_change_lkr": predicted - current,
                "predicted_change_pct": ((predicted - current) / current * 100.0) if current else None,
                "approx_lower_90": lower,
                "approx_upper_90": upper,
                "expected_leaf_kg": quantity,
                "estimated_gross_earnings_lkr": predicted * quantity,
                "gross_earnings_lower_90_lkr": lower * quantity,
                "gross_earnings_upper_90_lkr": upper * quantity,
                "reliability": reliability,
                "feature_completeness_pct": round(completeness * 100, 1),
                "reliable_history_months": history,
            }
        )

    results.sort(key=lambda item: item["predicted_reasonable_price"], reverse=True)
    for rank, item in enumerate(results, start=1):
        item["price_rank"] = rank

    return {
        "prediction_month": str(target_date.date()),
        "feature_month": str(feature_date.date()),
        "expected_leaf_kg": quantity,
        "comparison_basis": "predicted_reasonable_price_lkr_per_kg",
        "eligible_result_count": len(results),
        "returned_count": min(req.top_n, len(results)),
        "filters": {
            "district": req.district,
            "tea_growing_region": req.tea_growing_region,
            "elevation_category": req.elevation_category,
            "verified_geography_only": req.verified_geography_only,
        },
        "results": results[: req.top_n],
        "decision_support_note": (
            "Ranking is based only on predicted Reasonable Price. Distance, transport cost, "
            "leaf quality requirements, deductions, contracts, factory acceptance policies "
            "and other operational factors are not included."
        ),
    }


# ---------------------------------------------------------------------------
# Optional real-participant DSS evaluation collection
# ---------------------------------------------------------------------------
class EvaluationSubmission(BaseModel):
    participant_code: str | None = Field(None, max_length=40)
    role: str = Field(..., min_length=2, max_length=80)
    consent: bool
    task1_success: bool
    task2_success: bool
    task3_success: bool
    task4_success: bool
    task5_success: bool
    sus_q1: int = Field(..., ge=1, le=5)
    sus_q2: int = Field(..., ge=1, le=5)
    sus_q3: int = Field(..., ge=1, le=5)
    sus_q4: int = Field(..., ge=1, le=5)
    sus_q5: int = Field(..., ge=1, le=5)
    sus_q6: int = Field(..., ge=1, le=5)
    sus_q7: int = Field(..., ge=1, le=5)
    sus_q8: int = Field(..., ge=1, le=5)
    sus_q9: int = Field(..., ge=1, le=5)
    sus_q10: int = Field(..., ge=1, le=5)
    price_clarity_1to5: int = Field(..., ge=1, le=5)
    earnings_clarity_1to5: int = Field(..., ge=1, le=5)
    uncertainty_clarity_1to5: int = Field(..., ge=1, le=5)
    usefulness_1to5: int = Field(..., ge=1, le=5)
    trust_appropriateness_1to5: int = Field(..., ge=1, le=5)
    comments: str | None = Field(None, max_length=2000)


def _sus_score(values: list[int]) -> float:
    adjusted = []
    for index, value in enumerate(values, start=1):
        adjusted.append(value - 1 if index % 2 == 1 else 5 - value)
    return float(sum(adjusted) * 2.5)


@app.get("/evaluation/status")
def evaluation_status():
    count = 0
    if EVALUATION_DATA_PATH.is_file():
        try:
            count = max(0, sum(1 for _ in EVALUATION_DATA_PATH.open("r", encoding="utf-8")) - 1)
        except OSError:
            count = 0
    return {
        "collection_enabled": EVALUATION_ENABLED,
        "response_count": count,
        "privacy_note": (
            "The built-in form is designed for anonymized research responses and should only be "
            "enabled after any required university ethics/approval process."
        ),
    }


@app.post("/evaluation/submit")
def submit_evaluation(req: EvaluationSubmission):
    if not EVALUATION_ENABLED:
        raise HTTPException(
            status_code=403,
            detail=(
                "Evaluation collection is disabled. Set ENABLE_EVALUATION_COLLECTION=true only "
                "after the required ethics/approval process is complete."
            ),
        )
    if not req.consent:
        raise HTTPException(status_code=400, detail="Participant consent is required.")

    participant_code = (req.participant_code or f"P-{uuid.uuid4().hex[:8].upper()}").strip()
    sus_values = [getattr(req, f"sus_q{i}") for i in range(1, 11)]
    row = {
        "submitted_at_utc": datetime.now(timezone.utc).isoformat(),
        "participant_code": participant_code,
        "role": req.role.strip(),
        "task1_success": req.task1_success,
        "task2_success": req.task2_success,
        "task3_success": req.task3_success,
        "task4_success": req.task4_success,
        "task5_success": req.task5_success,
        **{f"sus_q{i}": getattr(req, f"sus_q{i}") for i in range(1, 11)},
        "sus_score": round(_sus_score(sus_values), 2),
        "price_clarity_1to5": req.price_clarity_1to5,
        "earnings_clarity_1to5": req.earnings_clarity_1to5,
        "uncertainty_clarity_1to5": req.uncertainty_clarity_1to5,
        "usefulness_1to5": req.usefulness_1to5,
        "trust_appropriateness_1to5": req.trust_appropriateness_1to5,
        "comments": (req.comments or "").strip(),
    }
    EVALUATION_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with EVALUATION_LOCK:
        exists = EVALUATION_DATA_PATH.is_file() and EVALUATION_DATA_PATH.stat().st_size > 0
        with EVALUATION_DATA_PATH.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(row.keys()))
            if not exists:
                writer.writeheader()
            writer.writerow(row)
    return {
        "status": "recorded",
        "participant_code": participant_code,
        "sus_score": row["sus_score"],
        "note": "Response stored without name, email, phone number or account identifier.",
    }
