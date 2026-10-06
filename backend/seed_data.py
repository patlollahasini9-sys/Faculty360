"""
Faculty360 — Seed the database with the 100 reference faculty records.
Run once after train_and_validate.py (models must exist for ML cross-check
predictions to be stored alongside each seeded record).

    cd backend
    python seed_data.py
"""
import sys
import os
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from scoring_engine import evaluate_faculty
from ml_engine import ml_predict, RAW_FEATURE_MAP
import database as db

CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "faculty360_dataset.csv")


def main():
    db.init_db()
    if db.count_evaluations() > 0:
        print(f"Database already has {db.count_evaluations()} records — skipping seed. "
              f"Delete backend/data/faculty360.db to re-seed from scratch.")
        return

    df = pd.read_csv(CSV_PATH)
    inserted = 0
    for _, row in df.iterrows():
        raw = {k: row[v] for k, v in RAW_FEATURE_MAP.items() if v in df.columns}
        raw["department"] = row["Department"]

        result = evaluate_faculty(raw)
        ml_result = ml_predict(raw)

        record = {
            "faculty_id": row["Faculty_ID"],
            "faculty_name": row["Faculty_ID"],  # names not in synthetic dataset
            "department": row["Department"],
            "experience_years": row["Experience_Years"],
            "semester": "Reference-Baseline",
            "raw_input": raw,
            "category_scores": result["category_scores"],
            "overall_score": result["overall_score"],
            "performance_category": result["performance_category"],
            "ml_predicted_score": ml_result.get("predicted_overall_score"),
            "ml_predicted_category": ml_result.get("predicted_performance_category"),
            "ml_confidence": ml_result.get("confidence"),
        }
        db.insert_evaluation(record)
        inserted += 1

    print(f"Seeded {inserted} reference faculty records into {db.DB_PATH}")


if __name__ == "__main__":
    main()
