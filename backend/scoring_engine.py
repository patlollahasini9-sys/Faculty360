"""
Faculty360 — Deterministic Scoring Engine
==========================================
Implements the exact weighted-indicator formula reverse-engineered from the
reference dataset (see config.py for the full derivation notes and
validation numbers). This is the PRIMARY, authoritative scoring path: given
any faculty member's raw metrics, it returns the same score a human
following the Faculty360 scoring framework by hand would compute — no
randomness, no model drift, fully explainable and auditable.

The ML layer (ml_engine.py) is a secondary, complementary layer used only
for classification cross-validation and pattern-based sanity-checking, as
recommended in the project's own design notes ("hybrid approach is
stronger and easier to justify" — Weighted Index for the baseline score,
ML for prediction/validation).
"""
from __future__ import annotations
from typing import Dict, Any, List, Tuple
from config import METRICS, CATEGORY_WEIGHTS, PERFORMANCE_BANDS


def _clip(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def _compute_sub_score(meta: Dict[str, Any], raw: Dict[str, Any]) -> float:
    """Compute one sub-metric score (0-100) from raw input fields."""
    mtype = meta["type"]

    if mtype == "direct":
        val = float(raw.get(meta["field"], 0) or 0)
        return round(_clip(val), 4)

    if mtype == "scale":
        val = float(raw.get(meta["field"], 0) or 0)
        return round(_clip(val / meta["scale_max"] * 100), 4)

    if mtype == "ratio":
        num = float(raw.get(meta["numerator"], 0) or 0)
        den = float(raw.get(meta["denominator"], 0) or 0)
        if den <= 0:
            return 0.0
        return round(_clip(num / den * 100), 4)

    if mtype == "count_cap":
        val = float(raw.get(meta["field"], 0) or 0)
        cap = meta["cap"]
        return round(_clip(val / cap * 100), 4)

    if mtype == "value_cap":
        val = float(raw.get(meta["field"], 0) or 0)
        cap = meta["cap"]
        return round(_clip(val, 0, cap) if cap == 100 else _clip(min(val, cap) / cap * 100), 4)

    raise ValueError(f"Unknown sub-metric type: {mtype}")


def classify_performance(overall_score: float) -> str:
    for lo, hi, label in PERFORMANCE_BANDS:
        if lo <= overall_score < hi:
            return label
    return PERFORMANCE_BANDS[0][2]


def evaluate_faculty(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entry point. `raw` is a flat dict of raw metric fields (see
    config.METRICS[*]['sub_metrics'][*]['field'] / 'numerator' / 'denominator'
    for the expected keys), plus optional faculty_id / faculty_name /
    department / experience_years.

    Returns a full breakdown: sub-scores, category scores, overall score,
    performance category, and the weakest areas for the recommendation
    engine to consume.
    """
    category_scores: Dict[str, float] = {}
    sub_score_detail: Dict[str, List[Dict[str, Any]]] = {}

    for cat_key, cat_def in METRICS.items():
        weighted_sum = 0.0
        details = []
        for sub_key, sub_meta in cat_def["sub_metrics"].items():
            score = _compute_sub_score(sub_meta, raw)
            weighted_sum += score * sub_meta["weight"]
            details.append({
                "key": sub_key,
                "label": sub_meta["label"],
                "score": score,
                "weight": sub_meta["weight"],
                "contribution": round(score * sub_meta["weight"], 4),
            })
        category_scores[cat_key] = round(weighted_sum, 2)
        sub_score_detail[cat_key] = details

    overall_score = round(
        sum(category_scores[c] * w for c, w in CATEGORY_WEIGHTS.items()), 2
    )
    overall_score = round(_clip(overall_score), 2)
    performance_category = classify_performance(overall_score)

    # Rank categories by (weight * gap-from-100) to find what most drags
    # the overall score down — feeds the recommendation engine.
    gaps = []
    for cat_key in METRICS:
        gap = (100 - category_scores[cat_key]) * CATEGORY_WEIGHTS[cat_key]
        gaps.append((cat_key, category_scores[cat_key], gap))
    gaps.sort(key=lambda x: -x[2])

    strengths = sorted(category_scores.items(), key=lambda x: -x[1])[:2]
    weaknesses = [g for g in gaps if g[1] < 75][:3] or [gaps[0]]

    return {
        "category_scores": category_scores,
        "sub_score_detail": sub_score_detail,
        "overall_score": overall_score,
        "performance_category": performance_category,
        "strengths": [{"category": c, "score": s} for c, s in strengths],
        "weaknesses": [{"category": c, "score": s, "impact": round(g, 2)} for c, s, g in weaknesses],
    }
