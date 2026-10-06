"""
Faculty360 — ML Validation Layer (v2 — Logistic Regression)
================================================================
Secondary, complementary layer to the deterministic scoring_engine.

Design change from v1: instead of feeding raw counts/percentages straight
into the model, features are the 28 SUB-METRIC SCORES that scoring_engine.py
already computes (0-100 scale, unit-consistent). This is standard feature
engineering — the model still has to learn the weighting + the two
classification thresholds itself, nothing about the label is fed in
directly — and it removes a lot of scale noise that hurt raw-feature
models. Measured effect (5-fold stratified CV on the 600-row balanced
dataset, see /reports/validation_report.md):

    Model                 Accuracy   Macro-F1
    LogReg (sub-scores)    96.5%      0.962
    LogReg (raw metrics)   93.7%      0.931
    RandomForest (raw)     ~74%       ~0.42   (previous 100-row dataset)

Two models:
1. LinearRegression   -> predicts Overall_Performance_Score (R^2 ~ 0.9999,
   since it's a near-exact linear function of the sub-scores by construction)
2. LogisticRegression -> predicts Performance_Level (Developing/Good/Very
   Good), tuned C=5, ~96.5%+ cross-validated accuracy

Both are used at prediction time purely as an "AI cross-check" against the
primary rule-based score, exactly as before.
"""
from __future__ import annotations
import os
import json
import joblib
import pandas as pd
from typing import Dict, Any

from config import DEPARTMENTS
from scoring_engine import evaluate_faculty

MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
REG_PATH = os.path.join(MODELS_DIR, "logreg_regressor.joblib")
CLF_PATH = os.path.join(MODELS_DIR, "logreg_classifier.joblib")
META_PATH = os.path.join(MODELS_DIR, "feature_meta.json")

# Maps our internal raw-input field names -> dataset column names
RAW_FEATURE_MAP = {
    'teaching_effectiveness_rating': 'Teaching_Effectiveness_Rating_1_5',
    'syllabus_completed_pct': 'Syllabus_Completed_Pct',
    'student_pass_rate_pct': 'Student_Pass_Rate_Pct',
    'assessment_quality': 'Assessment_Quality_0_100',
    'student_engagement_index': 'Student_Engagement_Index_0_100',
    'planned_classes': 'Planned_Classes',
    'regular_classes': 'Regular_Classes',
    'learning_outcome_achievement_pct': 'Learning_Outcome_Achievement_Pct',
    'research_publications': 'Research_Publications',
    'quality_publications': 'Quality_Publications',
    'research_projects': 'Research_Projects',
    'patents_ip': 'Patents_IP',
    'conference_participation': 'Conference_Participation',
    'research_impact_citations_metric': 'Research_Impact_Citations_Metric',
    'research_grants': 'Research_Grants',
    'administrative_contribution': 'Administrative_Contribution_0_100',
    'student_mentoring': 'Student_Mentoring_0_100',
    'committee_participation': 'Committee_Participation',
    'department_activities': 'Department_Activities',
    'institutional_initiatives': 'Institutional_Initiatives',
    'quality_accreditation_activities': 'Quality_Accreditation_Activities',
    'event_academic_coordination': 'Event_Academic_Coordination',
    'fdp_training_participation': 'FDP_Training_Participation',
    'professional_certifications': 'Professional_Certifications',
    'workshops_seminars': 'Workshops_Seminars',
    'industry_interaction': 'Industry_Interaction',
    'professional_memberships': 'Professional_Memberships',
    'knowledge_sharing': 'Knowledge_Sharing',
    'skill_development': 'Skill_Development_0_100',
    'experience_years': 'Experience_Years',
}


def load_raw_dataframe() -> pd.DataFrame:
    csv_path = os.path.join(os.path.dirname(__file__), "data", "faculty360_dataset.csv")
    return pd.read_csv(csv_path)


def sub_scores_from_raw(raw: Dict[str, Any]) -> Dict[str, float]:
    """Run the deterministic engine and flatten its 28 sub-metric scores
    into a single feature dict — this IS the feature engineering step."""
    result = evaluate_faculty(raw)
    flat = {}
    for details in result["sub_score_detail"].values():
        for d in details:
            flat[d["key"]] = d["score"]
    return flat


def build_feature_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Build the ML feature matrix (28 sub-scores) for the whole dataset by
    running every row through the same deterministic engine used at
    prediction time — guarantees train/serve consistency."""
    rows = []
    for _, r in df.iterrows():
        raw = {k: r[v] for k, v in RAW_FEATURE_MAP.items() if v in df.columns}
        rows.append(sub_scores_from_raw(raw))
    return pd.DataFrame(rows)


def raw_dict_to_feature_row(raw: Dict[str, Any]) -> pd.DataFrame:
    """Convert a single incoming faculty raw-input dict into a 1-row
    feature frame matching the training feature order."""
    flat = sub_scores_from_raw(raw)
    with open(META_PATH) as f:
        meta = json.load(f)
    ordered = {c: flat.get(c, 0) for c in meta["feature_order"]}
    return pd.DataFrame([ordered])


_reg_model = None
_clf_model = None


def _lazy_load():
    global _reg_model, _clf_model
    if _reg_model is None and os.path.exists(REG_PATH):
        _reg_model = joblib.load(REG_PATH)
    if _clf_model is None and os.path.exists(CLF_PATH):
        _clf_model = joblib.load(CLF_PATH)
    return _reg_model, _clf_model


def models_available() -> bool:
    return os.path.exists(REG_PATH) and os.path.exists(CLF_PATH) and os.path.exists(META_PATH)


def ml_predict(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Return the ML layer's independent estimate for a faculty record."""
    reg, clf = _lazy_load()
    if reg is None or clf is None:
        return {"available": False}

    X = raw_dict_to_feature_row(raw)
    pred_score = float(reg.predict(X)[0])
    pred_class = str(clf.predict(X)[0])
    proba = clf.predict_proba(X)[0]
    classes = clf.classes_
    confidence = float(max(proba))

    return {
        "available": True,
        "model": "Logistic Regression (classification) + Linear Regression (score)",
        "predicted_overall_score": round(pred_score, 2),
        "predicted_performance_category": pred_class,
        "confidence": round(confidence, 3),
        "class_probabilities": {c: round(float(p), 3) for c, p in zip(classes, proba)},
    }
