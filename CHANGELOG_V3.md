# V3 Research Completion Development

## Added

- `GET /regions` mapping-coverage and filter metadata endpoint.
- `GET /factory/{factory}/profile` geography-aware factory profile endpoint.
- Optional district / tea-growing region / elevation filters for `POST /compare-factories`.
- Geography fields in factory lists, individual forecasts, and comparison results.
- Full 104-factory mapping worksheet at `research/docs/factory_region_mapping.csv`.
- Mapping validation script that refuses guessed/unverified geography.
- Held-out 2025 regional/district/elevation performance and bias-analysis script.
- Optional anonymized DSS evaluation API, disabled by default.
- React **Research Evaluation** page with task completion, SUS, clarity, usefulness and trust ratings.
- Real-user evaluation analysis script; no synthetic participants are generated.
- Final thesis alignment guide and automatic evidence-status generator.
- Research-completion orchestrator.
- Docker support for the geography mapping and optional persistent user-evaluation response folder.
- Backend tests for mapping safeguards and evaluation collection.

## Research-integrity safeguards

- Regional analysis only uses mappings explicitly marked `Verified=True`.
- Regional filters fail closed when no verified geography exists.
- User-evaluation collection defaults to disabled.
- Evaluation submission requires consent.
- Built-in evaluation does not request names, emails or phone numbers.
- Thesis evidence generator leaves missing regional/user evidence marked pending.
- Owner outcome is labelled **gross earnings** unless costs are deducted.
