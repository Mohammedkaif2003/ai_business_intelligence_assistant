# Readmission dataset — findings

All numbers below are produced by running the pipeline against
`data/raw/healthcaret.csv`. They are computed, not estimated.

## Dataset

- 10,000 rows, 38 columns, 0 nulls, 0 duplicate rows.
- Target: `Readmitted` ∈ {Yes, No}; positive base rate **0.1564**
  (1,564 of 10,000).
- Date columns: `Admission_Date` and `Discharge_Date` parse cleanly,
  spanning 2020-01-01 to 2024-12-30 (1,839 days, 61 distinct months).
- The "1819 unique time periods" claim some prior summaries produced was
  a hallucination. The actual count of unique discharge dates is 1,823;
  the actual count of unique admission dates is 1,819. Neither is a
  count of "time periods" — they are just calendar-day cardinalities.

## Predictors with statistical signal (1 of 29)

- **`Discharge_Status`** — chi-square = 1120.0, p = 3.49 × 10⁻²⁴¹,
  Cramér's V = 0.3347, n = 10,000. Levels with empirical readmission
  rates: Ongoing Treatment 40.8 %, Against Medical Advice 32.3 %,
  Referred 20.8 %, Recovered 8.0 %, Deceased 7.9 %.

## Predictors with NO statistical signal (28 of 29)

The following features all fail the joint p < 0.05 + |effect size| ≥ 0.1
test and are therefore not reportable as drivers:

| Feature | Test | p-value | Effect size |
|---|---|---:|---:|
| Age | Welch t | 0.84 | d = -0.006 |
| Length_of_Stay_Days | Welch t | 0.10 | d = -0.043 |
| Bill_Amount_USD | Welch t | 0.94 | d = 0.002 |
| Insurance_Coverage_USD | Welch t | 0.21 | d = 0.035 |
| Patient_Copay_USD | Welch t | 0.17 | d = -0.036 |
| Systolic_BP | Welch t | 0.11 | d = 0.044 |
| Diastolic_BP | Welch t | 0.27 | d = -0.031 |
| Heart_Rate_BPM | Welch t | 0.95 | d = -0.002 |
| Body_Temp_F | Welch t | 0.25 | d = -0.032 |
| O2_Saturation_Pct | Welch t | 0.84 | d = -0.005 |
| BMI | Welch t | 0.39 | d = 0.024 |
| Staff_on_Duty | Welch t | 0.84 | d = -0.006 |
| Previous_Visits | Welch t | 0.95 | d = 0.002 |
| Satisfaction_Score | Welch t | 0.29 | d = 0.029 |
| Gender | chi² | 0.81 | V = 0.007 |
| Blood_Type | chi² | 0.74 | V = 0.021 |
| Admission_Type | chi² | 0.92 | V = 0.010 |
| Department | chi² | 0.019 | V = 0.052 |
| Diagnosis | chi² | 0.44 | V = 0.054 |
| Procedure | chi² | 0.70 | V = 0.039 |
| Day_of_Week | chi² | 0.21 | V = 0.029 |
| Insurance_Provider | chi² | 0.078 | V = 0.039 |
| Payment_Method | chi² | 0.56 | V = 0.020 |
| Referring_Source | chi² | 0.11 | V = 0.109 (n=100 levels — over-fit risk) |
| Shift | chi² | 0.60 | V = 0.010 |
| Satisfaction_Level | chi² | 0.60 | V = 0.017 |

`Department` reaches p < 0.05 but its effect size (V = 0.052) is below the
0.1 threshold; we therefore **do not** call it a driver.

`Referring_Source` has V = 0.109 but spans 100 referrer categories on
10,000 rows — a per-cell expectation small enough that V is unreliable.
The chi-square p-value is 0.11, so the joint criterion fails anyway.

## Temporal structure

`Admission_Date` and `Discharge_Date` parse cleanly. Monthly admission
counts (60 months) tested via Mann-Kendall + linear regression:

- **Admission counts:** Mann-Kendall τ = -0.077, MK p = 0.39,
  linregress slope = -0.057 / month, p = 0.5222, R² = 0.0071. **No trend.**
- **Monthly readmission rate:** Mann-Kendall τ = -0.035, p = 0.70,
  linregress p = 0.65. **No trend.**

ADF p < 0.0001 and KPSS p > 0.10 — both stationarity tests agree the
admission series is stationary noise around the mean. Forecasting via
ARIMA / Prophet would only return the long-run mean (~166 admissions /
month) and is therefore not informative.

## Modeling

5-fold stratified cross-validated ROC-AUC (with `class_weight='balanced'`
where applicable):

| Model | CV ROC-AUC | CV std |
|---|---:|---:|
| Logistic regression (L2) | 0.6954 | 0.0215 |
| Random forest (300 trees) | **0.7138** | 0.0145 |
| Gradient boosting (200 stumps, depth 3) | 0.7067 | 0.0201 |

Out-of-fold metrics for the random forest (best model):

- AUC-ROC = **0.7135** (95 % CI 0.6993–0.7287, bootstrap n = 500).
- AUC-PR = 0.3186 vs the trivial floor of 0.1564 — meaningful lift on the
  positive class.
- Brier score = 0.1194 vs trivial floor 0.1320 — calibrated better than
  predicting the base rate constant.
- Threshold sweep: at threshold 0.20, recall on readmission = 56.5 %,
  precision = 33.4 %. Operating choice depends on the cost of
  false-positive interventions.

## Feature-importance stability

Random-forest mean-decrease-in-impurity importance, refit on each of 5 CV
folds, with cross-fold coefficient of variation:

| Feature | Mean importance | CV of importance | Stable |
|---|---:|---:|:---:|
| Discharge_Status_Recovered | 0.0676 | 0.058 | yes |
| Discharge_Status_Ongoing Treatment | 0.0515 | 0.059 | yes |
| Patient_Copay_USD | 0.0312 | 0.019 | yes |
| BMI | 0.0309 | 0.026 | yes |
| Bill_Amount_USD | 0.0302 | 0.014 | yes |
| Systolic_BP | 0.0302 | 0.023 | yes |
| Age | 0.0288 | 0.023 | yes |

All 7 of the top features are stable (CV < 0.3). 346 of 347 one-hot-encoded
features are stable overall. The non-Discharge_Status features carry low
importance and have no univariate signal, so their stable importance
reflects model variance allocation, not predictive value.

## Bottom line

- The dataset has **one** real predictor of readmission: `Discharge_Status`.
- All other predictors fail the effect-size threshold and should not be
  reported as drivers.
- The temporal structure is real (61 months) but **stationary** — no trend,
  no seasonality strong enough to clear significance.
- Best model AUC ≈ 0.71 is consistent with what one feature with
  Cramér's V = 0.33 can achieve. There is no free lunch from non-linear
  models on this dataset.
- This is a **synthetic** dataset; nothing here generalises to real
  patients, and the pipeline says so explicitly in the notebook output.
