"""Pure matching/scoring orchestration - no DB access, so it stays easy to unit test.
Callers (API routes, bulk_processor) are responsible for persistence.
"""
from app.core.config import get_settings
from app.services import embedding_matcher, scoring, tfidf_matcher


def _text_similarity_pct(tfidf_sim: float, embedding_sim: float | None, skill_match_pct: float, settings) -> float:
    if embedding_sim is None:
        return tfidf_sim * 100

    total_weight = settings.tfidf_weight + settings.embedding_weight + settings.skill_weight
    if total_weight <= 0:
        return tfidf_sim * 100

    return 100 * (
        settings.tfidf_weight * tfidf_sim
        + settings.embedding_weight * embedding_sim
        + settings.skill_weight * (skill_match_pct / 100)
    ) / total_weight


def screen_candidates(job, candidates: list[dict]) -> list[dict]:
    """candidates: list of {"id", "filename", "raw_text", "structured_data"} for
    successfully-parsed resumes only. Returns ranked screening result dicts.
    """
    settings = get_settings()
    weights = job.scoring_weights or settings.default_weights

    resume_texts = [c["raw_text"] for c in candidates]
    tfidf_scores = tfidf_matcher.compute_tfidf_similarities(job.description, resume_texts)

    embedding_scores: list[float | None] = [None] * len(candidates)
    if settings.matching_method == "hybrid" and candidates:
        computed = embedding_matcher.compute_embedding_similarities(job.description, resume_texts)
        if computed is not None:
            embedding_scores = computed

    results = []
    for candidate, tfidf_sim, embedding_sim in zip(candidates, tfidf_scores, embedding_scores):
        structured = candidate.get("structured_data") or {}
        resume_skills = structured.get("skills", [])

        skill_result = scoring.compute_skill_match(
            resume_skills, job.must_have_skills or [], job.nice_to_have_skills or []
        )

        text_similarity_pct = _text_similarity_pct(
            tfidf_sim, embedding_sim, skill_result["skill_match_pct"], settings
        )

        experience_relevance = scoring.compute_experience_relevance(
            structured.get("experience", []), job.experience_requirements or []
        )
        education_relevance = scoring.compute_education_relevance(
            structured.get("education", []), job.education_requirements or []
        )

        overall_result = scoring.compute_overall_score(
            skill_result["skill_match_pct"],
            text_similarity_pct,
            experience_relevance,
            education_relevance,
            weights,
        )

        results.append(
            {
                "candidate_id": candidate["id"],
                "candidate_name": structured.get("name") or candidate.get("filename", ""),
                "filename": candidate.get("filename", ""),
                "status": "scored",
                "failure_reason": None,
                "score": {
                    "overall": overall_result["overall"],
                    "skill_match_pct": skill_result["skill_match_pct"],
                    "tfidf_similarity": round(tfidf_sim, 4),
                    "embedding_similarity": round(embedding_sim, 4) if embedding_sim is not None else None,
                    "weights_used": overall_result["weights_used"],
                },
                "skills": {
                    "matched": skill_result["matched"],
                    "missing": skill_result["missing"],
                    "missing_must_have": skill_result["missing_must_have"],
                    "missing_nice_to_have": skill_result["missing_nice_to_have"],
                },
            }
        )

    results.sort(key=lambda r: r["score"]["overall"], reverse=True)
    for rank, result in enumerate(results, start=1):
        result["ranking"] = rank

    return results
