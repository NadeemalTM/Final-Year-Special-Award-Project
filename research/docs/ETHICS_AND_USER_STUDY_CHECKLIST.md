# Ethics and Real User-Study Checklist

This checklist is operational guidance, not a substitute for NSBM's formal ethics requirements.

Before enabling participant collection:

- confirm whether ethics approval, exemption, module approval, or supervisor approval is required;
- use the approved participant information / consent process;
- recruit participants genuinely relevant to the study where practical;
- avoid collecting names, phone numbers, email addresses, NIC numbers, or unnecessary sensitive information;
- explain that forecasts are decision support rather than guaranteed future prices;
- explain that factory ranking currently excludes transport cost, distance, quality deductions, contracts and acceptance rules;
- allow participants to stop without penalty where required by the approved protocol;
- store responses securely and report results in aggregate.

To enable the built-in anonymized form after approval:

```text
ENABLE_EVALUATION_COLLECTION=true
```

Then restart FastAPI and open **Research Evaluation** in the React UI.

After real responses are collected:

```bash
python research/user_evaluation_analysis.py
python research/generate_thesis_evidence.py
```

Never create synthetic respondents and present them as real user evaluation.
