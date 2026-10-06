"""
Faculty360 — Smart Faculty Performance Evaluator
====================================================
Flask backend: serves the REST API + the static frontend.

Run:
    cd backend
    pip install -r requirements.txt
    python train_and_validate.py   # first time only (trains + saves ML models)
    python seed_data.py            # first time only (loads 100 reference records)
    python app.py
Then open http://127.0.0.1:5000
"""
import os
import sys
from flask import Flask, request, jsonify, send_from_directory

sys.path.insert(0, os.path.dirname(__file__))
import database as db
from scoring_engine import evaluate_faculty
from recommendations import build_recommendations
from ml_engine import ml_predict, models_available
from config import METRICS, DEPARTMENTS, RAW_FIELDS_META, CATEGORY_WEIGHTS, PERFORMANCE_BANDS

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
db.init_db()


# ---------------------------------------------------------------------------
# Static frontend
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


# ---------------------------------------------------------------------------
# Form schema — lets the frontend render the input form from config, so the
# form and the scoring engine can never drift out of sync.
# ---------------------------------------------------------------------------
@app.route("/api/form-schema")
def form_schema():
    schema = {"categories": {}, "departments": DEPARTMENTS, "category_weights": CATEGORY_WEIGHTS}
    for cat_key, cat_def in METRICS.items():
        fields = []
        for sub_key, meta in cat_def["sub_metrics"].items():
            if meta["type"] == "ratio":
                fields.append({
                    "key": meta["numerator"], "label": meta["input_label_num"],
                    "type": "number", "min": 0, "step": 1, "sub_metric": sub_key,
                })
                fields.append({
                    "key": meta["denominator"], "label": meta["input_label_den"],
                    "type": "number", "min": 0, "step": 1, "sub_metric": sub_key,
                })
            else:
                fields.append({
                    "key": meta["field"], "label": meta["input_label"],
                    "type": "number",
                    "min": meta.get("input_min", 0),
                    "max": meta.get("input_max"),
                    "step": meta.get("input_step", 1),
                    "sub_metric": sub_key,
                })
        schema["categories"][cat_key] = {
            "label": cat_key.replace("_", " ").title(),
            "weight": cat_def["weight"],
            "fields": fields,
        }
    return jsonify(schema)


# ---------------------------------------------------------------------------
# Core evaluation endpoint
# ---------------------------------------------------------------------------
@app.route("/api/evaluate", methods=["POST"])
def evaluate():
    payload = request.get_json(force=True)
    if not payload:
        return jsonify({"error": "Request body must be JSON"}), 400

    faculty_id = (payload.get("faculty_id") or "").strip()
    department = payload.get("department")
    if not faculty_id:
        return jsonify({"error": "faculty_id is required"}), 400
    if department not in DEPARTMENTS:
        return jsonify({"error": f"department must be one of {DEPARTMENTS}"}), 400

    raw = {k: v for k, v in payload.items()
           if k not in ("faculty_id", "faculty_name", "semester")}

    try:
        result = evaluate_faculty(raw)
    except Exception as e:
        return jsonify({"error": f"Scoring failed: {e}"}), 400

    recommendations = build_recommendations(result["sub_score_detail"])
    ml_result = ml_predict(raw)

    agreement = None
    if ml_result.get("available"):
        diff = abs(ml_result["predicted_overall_score"] - result["overall_score"])
        agreement = {
            "score_diff": round(diff, 2),
            "flag_for_review": diff > 10 or (
                ml_result["predicted_performance_category"] != result["performance_category"]
                and ml_result["confidence"] > 0.6
            ),
        }

    record = {
        "faculty_id": faculty_id,
        "faculty_name": payload.get("faculty_name"),
        "department": department,
        "experience_years": payload.get("experience_years"),
        "semester": payload.get("semester") or "Current",
        "raw_input": raw,
        "category_scores": result["category_scores"],
        "overall_score": result["overall_score"],
        "performance_category": result["performance_category"],
        "ml_predicted_score": ml_result.get("predicted_overall_score"),
        "ml_predicted_category": ml_result.get("predicted_performance_category"),
        "ml_confidence": ml_result.get("confidence"),
    }
    record_id = db.insert_evaluation(record)

    return jsonify({
        "id": record_id,
        "faculty_id": faculty_id,
        "faculty_name": payload.get("faculty_name"),
        "department": department,
        "category_scores": result["category_scores"],
        "sub_score_detail": result["sub_score_detail"],
        "overall_score": result["overall_score"],
        "performance_category": result["performance_category"],
        "strengths": result["strengths"],
        "weaknesses": result["weaknesses"],
        "recommendations": recommendations,
        "ml_cross_check": ml_result,
        "agreement": agreement,
    })


# ---------------------------------------------------------------------------
# Faculty list / detail / history
# ---------------------------------------------------------------------------
@app.route("/api/faculty")
def list_faculty():
    dept = request.args.get("department")
    rows = db.list_latest_per_faculty()
    if dept and dept != "All":
        rows = [r for r in rows if r["department"] == dept]
    return jsonify(rows)


@app.route("/api/faculty/<faculty_id>/history")
def faculty_history(faculty_id):
    hist = db.get_faculty_history(faculty_id)
    if not hist:
        return jsonify({"error": "Not found"}), 404
    return jsonify(hist)


@app.route("/api/faculty/<faculty_id>", methods=["DELETE"])
def delete_faculty(faculty_id):
    n = db.delete_faculty(faculty_id)
    return jsonify({"deleted": n})


# ---------------------------------------------------------------------------
# Dashboard aggregates
# ---------------------------------------------------------------------------
@app.route("/api/dashboard/summary")
def dashboard_summary():
    rows = db.list_latest_per_faculty()
    total = len(rows)
    by_level = {}
    for r in rows:
        by_level[r["performance_category"]] = by_level.get(r["performance_category"], 0) + 1

    by_department = {}
    for r in rows:
        d = r["department"]
        agg = by_department.setdefault(d, {"count": 0, "sum_overall": 0.0,
                                            "sum_teaching": 0.0, "sum_research": 0.0,
                                            "sum_institutional": 0.0, "sum_pd": 0.0})
        agg["count"] += 1
        agg["sum_overall"] += r["overall_score"]
        agg["sum_teaching"] += r["category_scores"]["teaching"]
        agg["sum_research"] += r["category_scores"]["research"]
        agg["sum_institutional"] += r["category_scores"]["institutional"]
        agg["sum_pd"] += r["category_scores"]["professional_development"]

    department_averages = []
    for d, agg in by_department.items():
        c = agg["count"]
        department_averages.append({
            "department": d, "count": c,
            "avg_overall": round(agg["sum_overall"] / c, 2),
            "avg_teaching": round(agg["sum_teaching"] / c, 2),
            "avg_research": round(agg["sum_research"] / c, 2),
            "avg_institutional": round(agg["sum_institutional"] / c, 2),
            "avg_professional_development": round(agg["sum_pd"] / c, 2),
        })

    avg_category = {"teaching": 0, "research": 0, "institutional": 0, "professional_development": 0}
    if total:
        for r in rows:
            for k in avg_category:
                avg_category[k] += r["category_scores"][k]
        avg_category = {k: round(v / total, 2) for k, v in avg_category.items()}

    top_performers = sorted(rows, key=lambda r: -r["overall_score"])[:5]
    bottom_performers = sorted(rows, key=lambda r: r["overall_score"])[:5]

    return jsonify({
        "total_faculty": total,
        "performance_distribution": by_level,
        "department_averages": sorted(department_averages, key=lambda x: -x["avg_overall"]),
        "average_category_scores": avg_category,
        "top_performers": [{"faculty_id": r["faculty_id"], "faculty_name": r["faculty_name"],
                             "department": r["department"], "overall_score": r["overall_score"],
                             "performance_category": r["performance_category"]} for r in top_performers],
        "bottom_performers": [{"faculty_id": r["faculty_id"], "faculty_name": r["faculty_name"],
                                "department": r["department"], "overall_score": r["overall_score"],
                                "performance_category": r["performance_category"]} for r in bottom_performers],
    })


@app.route("/api/validation-metrics")
def validation_metrics():
    path = os.path.join(os.path.dirname(__file__), "models", "validation_metrics.json")
    if not os.path.exists(path):
        return jsonify({"available": False,
                         "message": "Run `python train_and_validate.py` to generate validation metrics."})
    with open(path) as f:
        import json as _json
        data = _json.load(f)
    data["available"] = True
    return jsonify(data)


@app.route("/api/meta")
def meta():
    return jsonify({
        "departments": DEPARTMENTS,
        "category_weights": CATEGORY_WEIGHTS,
        "performance_bands": [{"min": lo, "max": hi, "label": lab} for lo, hi, lab in PERFORMANCE_BANDS],
        "ml_models_available": models_available(),
    })


if __name__ == "__main__":
    if not models_available():
        print("WARNING: ML models not found. Run `python train_and_validate.py` first "
              "for the AI cross-check layer to work. Rule-based scoring will still work.")
    app.run(debug=True, port=5000)
