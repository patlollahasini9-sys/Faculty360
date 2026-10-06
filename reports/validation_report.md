# Faculty360 — Validation Report
_Generated: 2026-09-11 08:04 UTC_

Dataset: `Faculty360_Improved_600_Balanced_Dataset.xlsx` — 600 faculty records, 7 departments, 3-tier balanced performance classes (Good=287, Developing=202, Very Good=111).

## 1. Deterministic Scoring Engine — Formula Validation
The scoring engine's weights/caps (see `config.py`) were reverse-engineered from the original reference dataset via linear regression, then re-applied from raw inputs end-to-end and checked against this 600-row dataset (including its classification thresholds at 58 and 75, also re-derived by inspection).

| Metric | Value |
|---|---|
| Records validated | 600 |
| Overall score — mean absolute error | 0.0041 |
| Overall score — max absolute error | 0.0100 |
| Teaching category — max absolute error | 0.0200 |
| Research category — max absolute error | 0.0000 |
| Institutional category — max absolute error | 0.0100 |
| Professional Development category — max absolute error | 0.0100 |
| Performance-category exact match rate | 100.0% (0 mismatches / 600) |

**Interpretation:** max errors are ≤0.02 points (floating-point rounding only), and all 600 reference records land in the identical performance band as the source dataset. New faculty entered through the app are scored on the same basis as this reference data.

## 2. ML Layer — Regression (Overall Score from engineered sub-score features)
**Model: LinearRegression (StandardScaler + LinearRegression, on 28 sub-score features).** Features are the 28 sub-metric scores the deterministic engine itself computes (0-100 scale, e.g. `teaching_effectiveness_score`, `research_publications_score`, ...) — not the raw uncleaned counts/percentages. Evaluated with 5-fold cross-validation (out-of-fold predictions, no leakage of the target itself).

| Metric | Model | Baseline (predict mean) |
|---|---|---|
| R² | 1.000000 | 0.0000 (by definition) |
| MAE | 0.0046 | 9.966 |
| RMSE | 0.0055 | — |

**Top 10 most influential sub-score features (standardized coefficient magnitude):**

| Feature | \|coefficient\| |
|---|---|
| research_publications_score | 1.632 |
| research_projects_score | 1.263 |
| quality_publications_score | 1.226 |
| research_impact_score | 1.215 |
| research_grants_score | 1.157 |
| teaching_effectiveness_score | 1.003 |
| student_engagement_score | 0.972 |
| learning_outcome_score | 0.899 |
| fdp_score | 0.892 |
| department_activities_score | 0.878 |

**Interpretation:** R² ≈ 1.0 is expected and correct here — Overall_Performance_Score *is*, by the framework's own design, an exact weighted linear combination of the category scores (which are themselves linear combinations of these sub-scores), so a linear model recovers it almost perfectly. This confirms the ML layer is faithfully reproducing the scoring framework rather than approximating something else.

## 3. ML Layer — Classification (Performance Level from engineered sub-score features)
**Model: LogisticRegression (StandardScaler + LogisticRegression, C=5.0, on 28 sub-score features).** Evaluated with 5-fold **StratifiedKFold (preserves class proportions in every fold)** — every fold has the same class proportions as the full dataset, so no class is over/under-represented in training or testing.

Class distribution: Good=287, Developing=202, Very Good=111 (out of 600 total) — reasonably balanced across all three performance tiers, unlike the earlier 100-row dataset.

| Metric | Model | Baseline (majority class) |
|---|---|---|
| **Accuracy** | **96.83%** | 47.8% |
| Macro F1 | 0.966 | — |
| Weighted F1 | 0.968 | — |

**Confusion matrix** (rows = actual, columns = predicted):

| Actual \ Predicted | Developing | Good | Very Good |
|---|---|---|---|
| **Developing** | 199 | 3 | 0 |
| **Good** | 5 | 277 | 5 |
| **Very Good** | 0 | 6 | 105 |

**Per-class report:**
```
              precision    recall  f1-score   support

  Developing       0.98      0.99      0.98       202
        Good       0.97      0.97      0.97       287
   Very Good       0.95      0.95      0.95       111

    accuracy                           0.97       600
   macro avg       0.97      0.97      0.97       600
weighted avg       0.97      0.97      0.97       600

```

**Interpretation:** almost all misclassifications occur for records that sit within ~1-2 points of the 58 or 75 threshold — i.e. genuinely borderline cases, not model failure. Because features are engineered (sub-scores instead of raw counts) and folds are stratified, this accuracy figure is a fair, reproducible estimate — not the result of tuning against the test set.

## 4. How scores/predictions are used together in the app
- **Primary result shown to the user:** the deterministic weighted-formula score and category (Section 1) — exact, explainable, auditable.
- **AI Cross-Check panel:** the Logistic/Linear Regression's independent estimate (Sections 2-3) is shown alongside it. If the two disagree, the UI flags the record for manual review.
- **Recommendations:** generated directly from the rule-based sub-metric breakdown, so every suggestion traces back to a specific under-performing indicator.

## 5. Reproducing this validation
```bash
cd backend
python train_and_validate.py
```
