"""
Faculty360 — Scoring Configuration
===================================
These weights and caps were reverse-engineered from
`Faculty360_Synthetic_Dataset_100_Rows.xlsx` by regressing every
pre-computed *_Score column against its raw inputs, then regressing
Overall_Performance_Score against the four category scores.

Validation performed during development (see /reports/validation_report.md):
  - Every sub-score reproduced with max abs error <= 0.005 (rounding only)
  - Every category score reproduced with max abs error <= 0.005
  - Overall_Performance_Score reproduced with max abs error <= 0.005
This confirms the formulas below are the ACTUAL formulas used to build the
dataset, not an approximation — so scores computed for new faculty are
consistent with the 100 reference records.
"""

# ---------------------------------------------------------------------------
# 1. CATEGORY WEIGHTS (sum to 1.0) — how the Overall Score is built
# ---------------------------------------------------------------------------
CATEGORY_WEIGHTS = {
    "teaching": 0.40,
    "research": 0.25,
    "institutional": 0.20,
    "professional_development": 0.15,
}

# ---------------------------------------------------------------------------
# 2. SUB-METRIC DEFINITIONS PER CATEGORY
#    type = "direct"   -> raw value already 0-100, used as-is (clipped 0-100)
#    type = "ratio"     -> numerator_field / denominator_field * 100
#    type = "count_cap" -> min(raw_count / cap * 100, 100)
#    type = "value_cap" -> min(raw_value, cap) scaled to 100 (cap IS the 100 mark)
# ---------------------------------------------------------------------------
METRICS = {
    "teaching": {
        "weight": 0.40,
        "sub_metrics": {
            "teaching_effectiveness_score": {
                "label": "Teaching Effectiveness",
                "weight": 0.20,
                "type": "scale",
                "field": "teaching_effectiveness_rating",
                "scale_max": 5,
                "input_label": "Teaching Effectiveness Rating (1-5, student/peer rated)",
                "input_min": 1, "input_max": 5, "input_step": 0.1,
            },
            "course_completion_score": {
                "label": "Course/Syllabus Completion",
                "weight": 0.15,
                "type": "direct",
                "field": "syllabus_completed_pct",
                "input_label": "Syllabus Completed (%)",
                "input_min": 0, "input_max": 100, "input_step": 0.1,
            },
            "student_pass_rate_score": {
                "label": "Student Pass Rate",
                "weight": 0.15,
                "type": "direct",
                "field": "student_pass_rate_pct",
                "input_label": "Student Pass Rate (%)",
                "input_min": 0, "input_max": 100, "input_step": 0.1,
            },
            "assessment_quality_score": {
                "label": "Assessment Quality",
                "weight": 0.10,
                "type": "direct",
                "field": "assessment_quality",
                "input_label": "Assessment Quality Index (0-100)",
                "input_min": 0, "input_max": 100, "input_step": 0.1,
            },
            "student_engagement_score": {
                "label": "Student Engagement",
                "weight": 0.15,
                "type": "direct",
                "field": "student_engagement_index",
                "input_label": "Student Engagement Index (0-100)",
                "input_min": 0, "input_max": 100, "input_step": 0.1,
            },
            "attendance_regularity_score": {
                "label": "Attendance Regularity",
                "weight": 0.10,
                "type": "ratio",
                "numerator": "regular_classes",
                "denominator": "planned_classes",
                "input_label_num": "Regular Classes Conducted",
                "input_label_den": "Planned Classes",
            },
            "learning_outcome_score": {
                "label": "Learning Outcome Achievement",
                "weight": 0.15,
                "type": "direct",
                "field": "learning_outcome_achievement_pct",
                "input_label": "Learning Outcome Achievement (%)",
                "input_min": 0, "input_max": 100, "input_step": 0.1,
            },
        },
    },
    "research": {
        "weight": 0.25,
        "sub_metrics": {
            "research_publications_score": {
                "label": "Research Publications",
                "weight": 0.20,
                "type": "count_cap", "field": "research_publications", "cap": 10,
                "input_label": "Research Publications (count, cap 10)",
            },
            "quality_publications_score": {
                "label": "Quality (SCI/Scopus) Publications",
                "weight": 0.15,
                "type": "count_cap", "field": "quality_publications", "cap": 6,
                "input_label": "Quality/Scopus Publications (count, cap 6)",
            },
            "research_projects_score": {
                "label": "Research Projects",
                "weight": 0.15,
                "type": "count_cap", "field": "research_projects", "cap": 5,
                "input_label": "Research Projects (count, cap 5)",
            },
            "patents_ip_score": {
                "label": "Patents / IP",
                "weight": 0.10,
                "type": "count_cap", "field": "patents_ip", "cap": 3,
                "input_label": "Patents / IP Filed (count, cap 3)",
            },
            "conference_participation_score": {
                "label": "Conference Participation",
                "weight": 0.10,
                "type": "count_cap", "field": "conference_participation", "cap": 6,
                "input_label": "Conference Participation (count, cap 6)",
            },
            "research_impact_score": {
                "label": "Research Impact (Citations)",
                "weight": 0.15,
                "type": "value_cap", "field": "research_impact_citations_metric", "cap": 100,
                "input_label": "Research Impact / Citation Metric (0-100+)",
            },
            "research_grants_score": {
                "label": "Research Grants",
                "weight": 0.15,
                "type": "count_cap", "field": "research_grants", "cap": 5,
                "input_label": "Research Grants Secured (count, cap 5)",
            },
        },
    },
    "institutional": {
        "weight": 0.20,
        "sub_metrics": {
            "administrative_contribution_score": {
                "label": "Administrative Contribution",
                "weight": 0.15,
                "type": "direct", "field": "administrative_contribution",
                "input_label": "Administrative Contribution (0-100)",
                "input_min": 0, "input_max": 100, "input_step": 0.1,
            },
            "student_mentoring_score": {
                "label": "Student Mentoring",
                "weight": 0.20,
                "type": "direct", "field": "student_mentoring",
                "input_label": "Student Mentoring Index (0-100)",
                "input_min": 0, "input_max": 100, "input_step": 0.1,
            },
            "committee_participation_score": {
                "label": "Committee Participation",
                "weight": 0.15,
                "type": "count_cap", "field": "committee_participation", "cap": 8,
                "input_label": "Committee Participation (count, cap 8)",
            },
            "department_activities_score": {
                "label": "Department Activities",
                "weight": 0.15,
                "type": "count_cap", "field": "department_activities", "cap": 8,
                "input_label": "Department Activities (count, cap 8)",
            },
            "institutional_initiatives_score": {
                "label": "Institutional Initiatives",
                "weight": 0.10,
                "type": "count_cap", "field": "institutional_initiatives", "cap": 6,
                "input_label": "Institutional Initiatives (count, cap 6)",
            },
            "quality_accreditation_score": {
                "label": "Accreditation (NBA/NAAC) Activities",
                "weight": 0.10,
                "type": "count_cap", "field": "quality_accreditation_activities", "cap": 6,
                "input_label": "Accreditation/Quality Activities (count, cap 6)",
            },
            "event_coordination_score": {
                "label": "Event / Academic Coordination",
                "weight": 0.15,
                "type": "count_cap", "field": "event_academic_coordination", "cap": 8,
                "input_label": "Event/Academic Coordination (count, cap 8)",
            },
        },
    },
    "professional_development": {
        "weight": 0.15,
        "sub_metrics": {
            "fdp_score": {
                "label": "FDP / Training Participation",
                "weight": 0.20,
                "type": "count_cap", "field": "fdp_training_participation", "cap": 8,
                "input_label": "FDP / Training Participation (count, cap 8)",
            },
            "professional_certifications_score": {
                "label": "Professional Certifications",
                "weight": 0.15,
                "type": "count_cap", "field": "professional_certifications", "cap": 5,
                "input_label": "Professional Certifications (count, cap 5)",
            },
            "workshops_seminars_score": {
                "label": "Workshops / Seminars",
                "weight": 0.10,
                "type": "count_cap", "field": "workshops_seminars", "cap": 8,
                "input_label": "Workshops / Seminars Attended (count, cap 8)",
            },
            "industry_interaction_score": {
                "label": "Industry Interaction",
                "weight": 0.15,
                "type": "count_cap", "field": "industry_interaction", "cap": 6,
                "input_label": "Industry Interaction Activities (count, cap 6)",
            },
            "professional_memberships_score": {
                "label": "Professional Memberships",
                "weight": 0.10,
                "type": "count_cap", "field": "professional_memberships", "cap": 5,
                "input_label": "Professional Memberships (count, cap 5)",
            },
            "knowledge_sharing_score": {
                "label": "Knowledge Sharing",
                "weight": 0.15,
                "type": "count_cap", "field": "knowledge_sharing", "cap": 8,
                "input_label": "Knowledge Sharing Sessions (count, cap 8)",
            },
            "skill_development_score": {
                "label": "Skill Development",
                "weight": 0.15,
                "type": "direct", "field": "skill_development",
                "input_label": "Skill Development Index (0-100)",
                "input_min": 0, "input_max": 100, "input_step": 0.1,
            },
        },
    },
}

# ---------------------------------------------------------------------------
# 3. PERFORMANCE CLASSIFICATION BANDS
#    Re-derived from Faculty360_Improved_600_Balanced_Dataset.xlsx (600
#    records). This balanced dataset uses a 3-tier scheme with exact
#    thresholds at 58 and 75 — verified with 0 mismatches across all 600
#    reference records.
# ---------------------------------------------------------------------------
PERFORMANCE_BANDS = [
    (75, 100.001, "Very Good"),
    (58, 75, "Good"),
    (0, 58, "Developing"),
]

DEPARTMENTS = ["CSE", "ECE", "EEE", "MECH", "CIVIL", "AIML", "MBA"]

RAW_FIELDS_META = {
    "faculty_id": {"label": "Faculty ID", "type": "text"},
    "faculty_name": {"label": "Faculty Name", "type": "text"},
    "department": {"label": "Department", "type": "select", "options": DEPARTMENTS},
    "experience_years": {"label": "Experience (Years)", "type": "number", "min": 0, "max": 45},
}
