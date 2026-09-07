# Factory → Region Mapping Guide

The proposal requires region-wise error analysis and bias assessment. The code is complete, but the geography itself must come from a **verified source**.

Open:

```text
research/docs/factory_region_mapping.csv
```

For every factory you can verify, fill:

- `District`
- `TeaGrowingRegion`
- `ElevationCategory`
- `Latitude` / `Longitude` if a reliable source provides them
- `Source` — official registry/report/page or other defensible source
- `Verified=True`
- `Notes` — ambiguity, alternate spelling, source date, etc.

Do **not** mark a row verified if the mapping was guessed from a factory name.

After editing:

```bash
python research/validate_factory_region_mapping.py
python research/regional_bias_analysis.py
```

The regional analysis will automatically restrict itself to verified rows and will report how much of the held-out 2025 test set is covered by verified geography.
