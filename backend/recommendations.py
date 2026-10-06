"""
Faculty360 — Recommendation Engine
====================================
Turns the weakest sub-metrics (lowest score * highest weight = biggest drag
on the overall score) into concrete, actionable suggestions. Rule-based and
fully explainable — every recommendation traces back to a specific
under-performing sub-metric.
"""
from typing import Dict, Any, List
from config import METRICS

ADVICE_LIBRARY = {
    "teaching_effectiveness_score": "Seek structured peer observation / mentoring to raise teaching-effectiveness ratings.",
    "course_completion_score": "Front-load the semester plan so syllabus completion doesn't slip in the final weeks.",
    "student_pass_rate_score": "Introduce diagnostic tests early in the semester to identify and support at-risk students sooner.",
    "assessment_quality_score": "Redesign assessments with clearer rubrics and a better mix of question difficulty.",
    "student_engagement_score": "Adopt active-learning techniques (flipped classroom, quizzes, discussions) to lift engagement.",
    "attendance_regularity_score": "Improve class regularity — reschedule proactively instead of cancelling classes.",
    "learning_outcome_score": "Map assessments more tightly to course outcomes (COs) to raise attainment.",
    "research_publications_score": "Target at least 1-2 peer-reviewed papers this year; start with conference papers if journal submissions are slow.",
    "quality_publications_score": "Aim future publications at SCI/Scopus-indexed venues for higher-quality output.",
    "research_projects_score": "Apply for a funded or collaborative research project this cycle.",
    "patents_ip_score": "Explore filing a patent/IP disclosure for any novel outcomes from current research or projects.",
    "conference_participation_score": "Present work at 2-3 conferences/seminars this year to build visibility and networks.",
    "research_impact_score": "Pursue collaborations with well-cited groups to build citation impact over time.",
    "research_grants_score": "Apply to at least one internal or external research grant scheme this cycle.",
    "administrative_contribution_score": "Take on a defined administrative role (lab in-charge, coordinator) to build institutional contribution.",
    "student_mentoring_score": "Formalize mentoring with regular one-on-one sessions and documented mentee outcomes.",
    "committee_participation_score": "Volunteer for at least 2-3 department/institute committees this year.",
    "department_activities_score": "Contribute to more department-level activities (events, orientation, outreach).",
    "institutional_initiatives_score": "Get involved in at least one institution-wide initiative (NEP alignment, digital learning, etc).",
    "quality_accreditation_score": "Support NBA/NAAC documentation and quality-assurance activities.",
    "event_coordination_score": "Coordinate or co-coordinate an academic event, workshop, or symposium.",
    "fdp_score": "Complete at least 2 FDPs/training programs this year — a quick, high-leverage improvement.",
    "professional_certifications_score": "Pursue one relevant professional certification to strengthen domain credentials.",
    "workshops_seminars_score": "Attend more discipline-relevant workshops/seminars for continuous exposure.",
    "industry_interaction_score": "Build at least one industry collaboration, guest lecture, or internship tie-up.",
    "professional_memberships_score": "Join a relevant professional body (IEEE, ISTE, ACM, etc).",
    "knowledge_sharing_score": "Run internal knowledge-sharing sessions or talks for peers/students.",
    "skill_development_score": "Dedicate time to a structured upskilling track (new tools, MOOCs) each semester.",
}

CATEGORY_LABELS = {
    "teaching": "Teaching Performance",
    "research": "Research",
    "institutional": "Institutional Contribution",
    "professional_development": "Professional Development",
}


def build_recommendations(sub_score_detail: Dict[str, List[Dict[str, Any]]], top_n: int = 5) -> List[Dict[str, Any]]:
    """
    Rank all sub-metrics across all categories by (100 - score) * weight
    (i.e. how much each one is costing the overall score) and return the
    top N as actionable recommendations.
    """
    candidates = []
    for cat_key, details in sub_score_detail.items():
        cat_weight = METRICS[cat_key]["weight"]
        for d in details:
            impact = (100 - d["score"]) * d["weight"] * cat_weight
            if d["score"] < 85:  # only flag genuine gaps
                candidates.append({
                    "category": CATEGORY_LABELS[cat_key],
                    "metric": d["label"],
                    "score": d["score"],
                    "impact": round(impact, 3),
                    "advice": ADVICE_LIBRARY.get(d["key"], "Focus on improving this area."),
                })

    candidates.sort(key=lambda x: -x["impact"])
    return candidates[:top_n]
