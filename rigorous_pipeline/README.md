# Rigorous tabular-prediction pipeline

A dataset-agnostic pipeline for tabular prediction that **enforces
statistical rigor in code**. Built for healthcare readmission analysis
but reusable for any binary / multiclass / regression target.

## Why this exists

Statistical pipelines that produce confident-sounding output on data with
no signal are worse than no pipeline at all. This repository implements
eight specific guardrails (see [`docs/MISTAKES_PREVENTED.md`](docs/MISTAKES_PREVENTED.md))
and ships a test suite that proves each guardrail catches its target
mistake on synthetic adversarial inputs.

## Layout

```
rigorous_pipeline/
├── pipeline/
│   ├── validation.py      # validate_dataset, check_temporal_structure, is_synthetic_or_random
│   ├── stats.py           # numeric_vs_binary, categorical_vs_binary, trend_test
│   ├── claim_verifier.py  # verify_claim, format_finding, BANNED_PHRASES
│   ├── modeling.py        # detect_task_type, train_models, baseline_score
│   ├── evaluation.py      # evaluate_binary, bootstrap_ci
│   └── interpret.py       # shap_importance, feature_stability, coefficient_ci
├── tests/                 # 48 unit + guardrail tests
├── notebooks/
│   └── readmission_analysis.ipynb
├── docs/
│   ├── MISTAKES_PREVENTED.md
│   ├── USAGE.md
│   └── FINDINGS_readmission.md
├── requirements.txt
└── .github/workflows/ci.yml
```

## Quickstart

```bash
pip install -r requirements.txt
pytest tests/ -v
```

Then open [`notebooks/readmission_analysis.ipynb`](notebooks/readmission_analysis.ipynb)
to see the pipeline applied to the bundled 10,000-row synthetic dataset.

## What the pipeline produces

For the bundled dataset, the headline numbers are:

- 1 of 29 features has statistical signal: `Discharge_Status`
  (Cramér's V = 0.33, p ≈ 3.5 × 10⁻²⁴¹)
- Best CV ROC-AUC = 0.7138 (random forest); 95 % bootstrap CI 0.699–0.729
- Monthly admissions are stationary white noise — no trend reportable

Full numbers, with computation traces, in [`docs/FINDINGS_readmission.md`](docs/FINDINGS_readmission.md).

## What this is NOT

- **Not** a substitute for clinical judgement. The bundled dataset is
  synthetic; nothing here generalises to real patients.
- **Not** a CMS-certified readmission risk score. Established clinical
  scores (LACE, HOSPITAL, CMS Hospital-Wide Readmission) require
  comorbidity codes, ED-visit history, and admission-source data that
  the synthetic file does not contain.
- **Not** a deep-learning framework. The architecture is deliberately
  shallow — interpretability is the priority.

## Reading the codebase

Start with [`pipeline/claim_verifier.py`](pipeline/claim_verifier.py).
Every text artefact in the notebook is rendered through `format_finding()`
and validated against `verify_claim()`; understanding that pair is the
shortest path to understanding what the rest of the pipeline guarantees.
