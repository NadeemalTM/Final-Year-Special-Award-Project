"""Validate the verified factory geography mapping before regional analysis."""
from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MAPPING = ROOT / "research" / "docs" / "factory_region_mapping.csv"
FEATURE_STORE = ROOT / "prediction_feature_store.csv"
OUT = ROOT / "research" / "results" / "regional_analysis" / "mapping_validation.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

REQUIRED = [
    "Factory", "FactoryName", "District", "TeaGrowingRegion", "ElevationCategory",
    "Latitude", "Longitude", "Source", "Verified", "Notes"
]


def truth(v):
    return str(v).strip().lower() in {"true", "1", "yes", "verified"}


def main():
    mapping = pd.read_csv(MAPPING, dtype={"Factory": str})
    missing_cols = [c for c in REQUIRED if c not in mapping.columns]
    if missing_cols:
        raise ValueError(f"Missing mapping columns: {missing_cols}")
    feature = pd.read_csv(FEATURE_STORE, usecols=["Factory", "eligible_factory"])
    eligible = sorted(feature.loc[feature["eligible_factory"].map(truth), "Factory"].astype(str).unique())
    mapping["Factory"] = mapping["Factory"].astype(str).str.strip()
    mapping["Verified"] = mapping["Verified"].map(truth)
    verified = mapping.loc[mapping["Verified"]].copy()

    problems = []
    dup = mapping.loc[mapping["Factory"].duplicated(keep=False), "Factory"].unique().tolist()
    if dup:
        problems.append({"type": "duplicate_factory_codes", "values": dup})

    for row in verified.itertuples(index=False):
        missing = []
        for col in ["District", "TeaGrowingRegion", "ElevationCategory", "Source"]:
            value = getattr(row, col)
            if pd.isna(value) or str(value).strip() == "":
                missing.append(col)
        if missing:
            problems.append({"type": "verified_row_missing_required_metadata", "factory": row.Factory, "missing": missing})
        for col, lower, upper in [("Latitude", -90, 90), ("Longitude", -180, 180)]:
            value = getattr(row, col)
            if not pd.isna(value):
                try:
                    number = float(value)
                    if not lower <= number <= upper:
                        problems.append({"type": "invalid_coordinate", "factory": row.Factory, "column": col, "value": value})
                except ValueError:
                    problems.append({"type": "invalid_coordinate", "factory": row.Factory, "column": col, "value": value})

    unknown = sorted(set(mapping["Factory"]) - set(eligible))
    missing_rows = sorted(set(eligible) - set(mapping["Factory"]))
    summary = {
        "eligible_factory_count": len(eligible),
        "mapping_row_count": int(len(mapping)),
        "verified_factory_count": int(verified["Factory"].nunique()),
        "verified_coverage_pct": round(verified["Factory"].nunique() / len(eligible) * 100, 2) if eligible else 0,
        "unknown_or_ineligible_factory_codes": unknown,
        "eligible_factories_missing_mapping_rows": missing_rows,
        "problem_count": len(problems),
        "problems": problems,
        "status": "ready_for_regional_analysis" if len(problems) == 0 and len(verified) > 0 else "needs_mapping_work",
    }
    OUT.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
