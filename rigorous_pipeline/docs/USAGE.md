# Applying this pipeline to a new dataset

The pipeline is dataset-agnostic. To analyse a new tabular dataset:

## 1. Install

```bash
pip install -r requirements.txt
```

## 2. Load and validate

```python
import pandas as pd
from pipeline import validate_dataset, is_synthetic_or_random

df = pd.read_csv("path/to/your.csv")
report = validate_dataset(df)
print(report.to_dict())

syn = is_synthetic_or_random(df, target="<your_target_column>")
if syn.is_likely_synthetic:
    print("WARNING: dataset shows no significant signal — modeling will not "
          "exceed baseline.")
```

## 3. Per-feature univariate screening

```python
from pipeline import numeric_vs_binary, categorical_vs_binary, format_finding, verify_claim

y = (df["<target>"] == "<positive_value>").astype(int)
results = []
for col in numeric_columns:
    r = numeric_vs_binary(df[col], y)
    msg = format_finding(r)
    if not verify_claim(msg, evidence=r).accepted:
        raise RuntimeError(f"non-compliant finding produced for {col}: {msg}")
    results.append(r)
    print(msg)
```

The same shape works for `categorical_vs_binary` and `numeric_vs_numeric`.

## 4. Test for temporal structure before any time-series claim

```python
from pipeline import check_temporal_structure, trend_test

tmp = check_temporal_structure(df)
if tmp.has_temporal_structure:
    parsed = pd.to_datetime(df[tmp.date_column], dayfirst=True)
    monthly = df.set_index(parsed).resample("ME").size()
    print(format_finding(trend_test(monthly)))
else:
    print("No temporal claims will be made.")
```

## 5. Train models and evaluate

```python
from pipeline import detect_task_type, train_models, baseline_score, evaluate_binary

task = detect_task_type(df["<target>"])
print("baseline:", baseline_score(df["<target>"], task))
results = train_models(df[features], df["<target>"], cv_folds=5)
best = max(results.values(), key=lambda r: r.cv_mean)
ev = evaluate_binary(y.values, best.oof_predictions)
print(f"AUC = {ev.auc_roc:.4f} (95% CI {ev.auc_roc_ci95})")
```

## 6. Cross-fold importance stability

```python
from pipeline import feature_stability
stab = feature_stability(my_estimator_factory, X, y, cv_folds=5)
print(stab.table[stab.table.stable].head(10))
```

## What the pipeline expects

- A pandas DataFrame with a clearly named target column.
- Numeric columns are auto-standardised inside the modeling pipeline; you
  don't need to scale upstream.
- Non-numeric columns are one-hot encoded with `handle_unknown='ignore'`,
  so unseen categories at inference time produce zero rows in the OHE
  matrix rather than crashing.
- Class imbalance is handled by `class_weight='balanced'` for logistic
  regression and random forest (default). To use SMOTE instead, pass
  `handle_imbalance=False` to `train_models` and apply SMOTE upstream.

## What the pipeline will refuse to do

- Compute trends on a series shorter than 8 points.
- Treat a numeric column as a date column.
- Print a directional claim ("X impacts Y", "rates are increasing")
  without paired statistics — `verify_claim` returns
  `accepted=False` and the test suite proves this on every banned phrase.
- Mark a feature as predictive when |effect size| is below the threshold
  (default 0.1 for Cohen's d / Cramér's V). p < 0.05 alone is not enough.

## Failure modes you should expect

If `is_synthetic_or_random` returns `True`, every model in `train_models`
will score near the baseline. The pipeline does not interpret this as
"the model failed" — it interprets it as "the data has no signal" and
makes that the explicit message.
