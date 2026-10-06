"""
Faculty360 — Database Layer (SQLite)
=======================================
Stores every evaluation submission (raw inputs + computed results) so the
dashboard has real data to aggregate, and so a faculty member's history can
be tracked across semesters/submissions over time.
"""
import sqlite3
import json
import os
from datetime import datetime, timezone
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "faculty360.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS evaluations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    faculty_id TEXT NOT NULL,
    faculty_name TEXT,
    department TEXT NOT NULL,
    experience_years REAL,
    semester TEXT,
    raw_input_json TEXT NOT NULL,
    category_scores_json TEXT NOT NULL,
    overall_score REAL NOT NULL,
    performance_category TEXT NOT NULL,
    ml_predicted_score REAL,
    ml_predicted_category TEXT,
    ml_confidence REAL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_faculty_id ON evaluations(faculty_id);
"""


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_conn()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


def insert_evaluation(record: dict) -> int:
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO evaluations
           (faculty_id, faculty_name, department, experience_years, semester,
            raw_input_json, category_scores_json, overall_score, performance_category,
            ml_predicted_score, ml_predicted_category, ml_confidence, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            record["faculty_id"], record.get("faculty_name"), record["department"],
            record.get("experience_years"), record.get("semester"),
            json.dumps(record["raw_input"]), json.dumps(record["category_scores"]),
            record["overall_score"], record["performance_category"],
            record.get("ml_predicted_score"), record.get("ml_predicted_category"),
            record.get("ml_confidence"),
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["raw_input"] = json.loads(d.pop("raw_input_json"))
    d["category_scores"] = json.loads(d.pop("category_scores_json"))
    return d


def list_latest_per_faculty() -> list:
    """One row per faculty_id — their most recent evaluation."""
    conn = get_conn()
    rows = conn.execute(
        """SELECT e.* FROM evaluations e
           INNER JOIN (
               SELECT faculty_id, MAX(id) AS max_id FROM evaluations GROUP BY faculty_id
           ) latest ON e.id = latest.max_id
           ORDER BY e.overall_score DESC"""
    ).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def get_faculty_history(faculty_id: str) -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM evaluations WHERE faculty_id = ? ORDER BY created_at ASC",
        (faculty_id,),
    ).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def get_latest_evaluation(faculty_id: str) -> Optional[dict]:
    hist = get_faculty_history(faculty_id)
    return hist[-1] if hist else None


def count_evaluations() -> int:
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) FROM evaluations").fetchone()[0]
    conn.close()
    return n


def delete_faculty(faculty_id: str) -> int:
    conn = get_conn()
    cur = conn.execute("DELETE FROM evaluations WHERE faculty_id = ?", (faculty_id,))
    conn.commit()
    n = cur.rowcount
    conn.close()
    return n
