# How the pipeline prevents the 8 listed mistakes

Each mistake below maps to a specific guardrail in `pipeline/`, a test in
`tests/`, and a behaviour the user can verify directly. Numbers cited under
"Observed on the readmission dataset" are produced by running the actual
pipeline against `data/raw/healthcaret.csv` (n = 10,000 rows, 38 columns,
0 nulls, 0 duplicates).

---

## Mistake 1 — Hallucinated time series

**The mistake:** Claiming "1819 time periods" or any other temporal
structure without verifying that a date column exists, parses cleanly, and
has meaningful variance.

**Guardrail:** `pipeline.validation.check_temporal_structure(df, ...)` ➜
returns a `TemporalReport` with `has_temporal_structure: bool` plus the
exact reason. It refuses to consider a column a date column unless ≥ 90 %
of values parse, ≥ 30 unique dates exist, span ≥ 30 days, and ≥ 12 distinct
months are observed. Numeric columns are explicitly skipped because
`pd.to_datetime` would interpret floats as nanosecond timestamps.

**Tests:** `tests/test_validation.py::test_check_temporal_structure_*` and
`tests/test_guardrails.py::test_mistake1_*`.

**Observed on readmission data:** `has_temporal_structure = True`,
`date_column = 'Discharge_Date'`, **1823 unique dates** spanning **1839
days** across **61 months**. The "1819 time periods" claim was the original
hallucination — the real number is 1823, and it refers to unique discharge
dates, **not** time periods of any aggregated series. Monthly aggregation
produces 60 buckets (a real number, computed not estimated).

---

## Mistake 2 — Spurious trend claims

**The mistake:** Asserting "admissions are trending upward" without a slope
coefficient or significance test, especially on synthetic / shuffled data.

**Guardrail:** `pipeline.stats.trend_test(series)` runs **both**
Mann-Kendall and OLS linear regression and returns `is_significant=True`
only when **both** p-values are below α. The conservative joint requirement
keeps nominal false-positive rates well below 5 %. The claim verifier
additionally blocks the phrases "trending up", "trending upward", "trends
upward", "trending downward" etc. unless they are accompanied by a
p-value.

**Tests:** `tests/test_stats.py::test_trend_test_refuses_to_find_trend_in_noise`,
`tests/test_guardrails.py::test_mistake2_trend_on_shuffled_data_is_rejected`,
`test_mistake2_directional_phrase_alone_blocked_by_verifier`.

**Observed on readmission data:** monthly admission count series across 60
months returns slope = -0.057 / month, linregress p = 0.5222, Mann-Kendall
τ = -0.077. **No trend is reportable.** The monthly readmission-rate series
is similarly flat (Mann-Kendall p ≈ 0.70). The system therefore prints
"No statistically significant association between 'series' and target ..."
and refuses to use directional language.

---

## Mistake 3 — Correlation as causation

**The mistake:** "X impacts Y" without coefficient, p-value, effect size,
or sample size.

**Guardrail:** `verify_claim(text, evidence)` rejects any claim containing
DIRECTIONAL_WORDS ("impact", "drives", "causes", "predicts", "associated"
etc.) when neither the text nor the evidence dictionary supplies a
p-value, effect size, and n. `format_finding(stat_result)` is the
recommended way to produce a compliant string — it always includes all
required fields.

**Tests:** `tests/test_claim_verifier.py::test_rejects_directional_claim_without_supporting_stats`,
`test_rejects_relationship_claim_when_evidence_is_nonsignificant`,
`tests/test_guardrails.py::test_mistake3_*`.

---

## Mistake 4 — EDA narration confused with prediction

**The mistake:** Reporting summary statistics ("average length of stay is
4.1 days") as if they were predictive insights.

**Guardrail:** Three separate layers — `validation.py` returns descriptive
counts only; `stats.py` returns hypothesis-test artefacts; `modeling.py` is
the only path that produces a prediction. The claim verifier rejects the
word "predicts" without supporting statistics. Every prediction artefact
is paired with the baseline score so the reader cannot mistake "84 %
accuracy from majority class" for predictive value.

**Tests:** `tests/test_modeling.py::test_baseline_score_binary_reports_majority_share`,
`tests/test_guardrails.py::test_mistake4_summary_stats_alone_do_not_pass_verifier`.

**Observed on readmission data:** baseline accuracy = 0.8436, baseline
recall on the positive class = 0.0. Models are reported as ROC-AUC, not
accuracy, precisely so that this trap is avoided.

---

## Mistake 5 — Unvalidated feature importance

**The mistake:** Reporting top features from a single model fit without
checking they reproduce across folds.

**Guardrail:** `pipeline.interpret.feature_stability(estimator_factory, X,
y, cv_folds)` refits the model on each CV fold, computes the per-fold
importance, and reports the cross-fold coefficient of variation. Features
with CV ≥ 0.3 are flagged unstable.

**Tests:** `tests/test_guardrails.py::test_mistake5_importance_must_carry_stability_metadata`.

**Observed on readmission data:** of 347 one-hot-encoded features in the
random-forest model, **346 are flagged stable** (CV of importance < 0.3).
The two highest-importance features are `Discharge_Status_Recovered`
(mean = 0.0676, CV = 0.0584) and `Discharge_Status_Ongoing Treatment`
(0.0515, CV = 0.0593) — by far the most stable, matching the univariate
chi-square result.

---

## Mistake 6 — Vague hedging language

**The mistake:** "may indicate", "could suggest", "appears to" — language
that sounds analytical but commits to nothing.

**Guardrail:** `pipeline.claim_verifier.BANNED_PHRASES` is a literal list
of 18 hedging phrases (and their conjugations). `verify_claim` rejects any
text containing them. The non-significant version of `format_finding`
explicitly says "No statistically significant association between X and
target".

**Tests:** `tests/test_claim_verifier.py::test_rejects_each_listed_banned_phrase`,
`tests/test_guardrails.py::test_mistake6_all_listed_hedge_phrases_blocked`.

---

## Mistake 7 — Silent failure on synthetic / random data

**The mistake:** Producing confident-sounding output on a dataset that has
no signal at all.

**Guardrail:** `pipeline.validation.is_synthetic_or_random(df, target)`
computes feature-vs-target mutual information and absolute correlation;
when the maximum MI across all features is below 0.05 the dataset is
flagged. The evaluation layer additionally appends a "AUC near random"
note when `auc_roc < 0.55`, and the modeling tests verify that algorithms
collapse to the baseline on noise.

**Tests:** `tests/test_validation.py::test_is_synthetic_or_random_flags_pure_noise`,
`tests/test_modeling.py::test_models_collapse_to_baseline_on_pure_noise`,
`tests/test_guardrails.py::test_mistake7_synthetic_data_is_flagged_loudly`,
`test_endtoend_pipeline_refuses_to_fabricate_insight_on_noise`.

**Observed on readmission data:** `is_likely_synthetic = False`,
max MI = 0.0536 (just above the 0.05 threshold), max |correlation| = 0.1448.
The signal comes entirely from `Discharge_Status` — every other feature
fails univariate testing. The pipeline says so explicitly: of 29 candidate
predictors, **only 1 passes** the joint p < 0.05 + effect-size threshold.

---

## Mistake 8 — Inventing row counts and metrics

**The mistake:** Reporting numbers from memory or estimation rather than
from a computation on the actually loaded data.

**Guardrail:** Every numeric output in `validate_dataset`, `baseline_score`,
`evaluate_binary`, and `format_finding` is computed inline from the
DataFrame or the model's prediction array. Tests assert that the reported
count exactly equals `len(df)` for unusual numbers (e.g., n = 137) so any
constant-default would fail.

**Tests:** `tests/test_validation.py::test_validate_dataset_counts_are_computed_not_estimated`,
`tests/test_guardrails.py::test_mistake8_validation_report_numbers_match_actual_dataframe`.
