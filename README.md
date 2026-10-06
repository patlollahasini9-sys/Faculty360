# Faculty360 — Smart Faculty Performance Evaluator

A full-stack faculty performance evaluation system: enter a faculty
member's raw metrics for a semester and instantly get an accurate,
explainable performance score, category, AI cross-check, and personalized
improvement recommendations — built on a scoring formula reverse-engineered
and validated directly against `Faculty360_Improved_600_Balanced_Dataset.xlsx`.

## Why the scores are accurate

Rather than inventing a new formula, the engine's weights and caps for
every one of the 28 sub-metrics were **derived from the reference dataset
itself** (linear regression of each pre-computed score column against its
raw inputs), then re-applied end-to-end and checked back against all 600
records. Result: **≤0.02-point max error and 600/600 exact classification
match** — see `reports/validation_report.md`. New faculty entered through
the app are scored on exactly the same basis as the reference data.

On top of that deterministic baseline, a **Logistic Regression** classifier
+ **Linear Regression** regressor — trained on the 28 engineered sub-score
features rather than raw counts — run as a secondary **AI cross-check**:

| Model | Metric | Result |
|---|---|---|
| Logistic Regression (Performance Level) | 5-fold Stratified CV accuracy | **96.83%** |
| Logistic Regression | Macro F1 | 0.966 |
| Linear Regression (Overall Score) | 5-fold CV R² | 0.999999 |

If the ML model's independent estimate disagrees sharply with the formula
score, the UI flags the record for review. This is the hybrid design
recommended in the project brief: weighted index for the authoritative
score, ML for prediction/validation, not the other way round.

## Project structure

```
faculty360/
├── backend/
│   ├── app.py                 # Flask API + serves the frontend
│   ├── config.py              # Weights, caps, bands — single source of truth
│   ├── scoring_engine.py      # Deterministic weighted scoring (validated)
│   ├── recommendations.py     # Rule-based recommendation engine
│   ├── ml_engine.py           # Feature engineering + Logistic/Linear Regression
│   ├── train_and_validate.py  # Trains models + writes the validation report
│   ├── seed_data.py           # Loads the 600 reference rows into the DB
│   ├── database.py            # SQLite persistence layer
│   ├── requirements.txt
│   ├── data/
│   │   ├── Faculty360_Improved_600_Balanced_Dataset.xlsx
│   │   ├── faculty360_dataset.csv     # Same data, as CSV (used by the app)
│   │   └── faculty360.db              # Created on first run
│   └── models/                        # Created by train_and_validate.py
│       ├── logreg_regressor.joblib
│       ├── logreg_classifier.joblib
│       ├── feature_meta.json
│       └── validation_metrics.json
├── frontend/
│   ├── index.html             # Dashboard / Evaluate / Roster / Validation SPA
│   ├── css/style.css
│   └── js/app.js
└── reports/
    └── validation_report.md   # Full validation write-up (human-readable)
```

## Setup & run

Requires Python 3.9+.

```bash
cd faculty360/backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

python train_and_validate.py    # trains models, writes validation_report.md
python seed_data.py             # loads the 600 reference faculty into the DB

python app.py
```

Open **http://127.0.0.1:5000** in your browser.

> Re-run `train_and_validate.py` any time you add real institutional data to
> `backend/data/faculty360_dataset.csv` (keep the same column names) — it
> retrains both models and regenerates the validation report automatically.

## Using the app

- **Dashboard** — institution-wide KPIs, performance distribution,
  department comparison, top/bottom performers.
- **Evaluate Faculty** — enter one faculty member's raw metrics (grouped by
  Teaching / Research / Institutional / Professional Development, exactly
  mirroring the scoring framework); submit to get the score, category, AI
  cross-check, and ranked recommendations, saved to the roster.
- **Faculty Roster** — every faculty member's latest evaluation, filterable
  by department, click through to a radar chart + score-trend history.
- **Model Validation** — the metrics above, rendered live from
  `validation_metrics.json`.

## Scoring formula reference

| Category | Weight | Key sub-metrics |
|---|---|---|
| Teaching | 40% | Effectiveness rating, syllabus completion, pass rate, assessment quality, engagement, attendance regularity, learning-outcome attainment |
| Research | 25% | Publications, quality publications, projects, patents/IP, conferences, citation impact, grants |
| Institutional | 20% | Administrative contribution, mentoring, committees, department activities, institutional initiatives, accreditation work, event coordination |
| Professional Development | 15% | FDPs/training, certifications, workshops, industry interaction, memberships, knowledge sharing, skill development |

`Overall = 0.40×Teaching + 0.25×Research + 0.20×Institutional + 0.15×ProfDev`

Performance bands (re-derived from this dataset, 0 mismatches across all
600 records): **Very Good** ≥75 · **Good** 58-75 · **Developing** <58.

## Why Logistic Regression reaches 96%+ (and how that number was earned)

The earlier 100-row dataset topped out around 87-88% no matter the model,
because its "Very Good" class had exactly 1 example — no cross-validation
scheme can fairly validate a class with 1 sample. This 600-row balanced
dataset fixes that (Developing=202, Good=287, Very Good=111), which is
what actually unlocked higher, *honestly measured* accuracy — not a model
swap by itself.

The second change that mattered: features fed to the classifier are the
**28 sub-metric scores the scoring engine already computes** (0-100 scale,
unit-consistent) rather than raw mixed-unit counts/percentages/ratios. This
is standard feature engineering, not label leakage — the model still has
to learn the category weighting and the two classification thresholds
itself. Measured on identical folds:

| Model / Features | Accuracy |
|---|---|
| Logistic Regression, sub-score features | **96.83%** |
| Logistic Regression, raw metric features | 93.7% |
| Random Forest, raw metric features | ~74-88% (varies by CV scheme) |

All numbers use `StratifiedKFold(n_splits=5)` — out-of-fold predictions
only, no peeking at test data during training. Full confusion matrix and
per-class report are in `reports/validation_report.md`.

## Known limitations (see validation report for full detail)

- Remaining classification errors cluster at faculty within ~1-2 points of
  the 58 or 75 thresholds — genuinely borderline cases, not model failure.
- The Linear Regression R² is ≈1.0 by construction (Overall Score is an
  exact linear function of the sub-scores) — this validates that the ML
  layer faithfully reproduces the formula, it isn't evidence of predicting
  something independently noisy.
- `Research_Impact_Citations_Metric` and the `*_0_100` fields are treated
  as pre-normalized indices — if your institution computes these
  differently, adjust the corresponding entries in `backend/config.py`.
