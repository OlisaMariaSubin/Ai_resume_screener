"""Gemini-generated match explanations (Section 9.2). Grounded strictly in the
score/skills data already computed elsewhere - never invents facts, never
recommends hire/reject.
"""
import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)

UNAVAILABLE_MESSAGE = "explanations unavailable"

SYSTEM_PROMPT = (
    "You explain candidate-job match scores for a recruiter. You are given only "
    "structured score and skill data - never invent skills, experience, or facts "
    "not present in that data. Write 2-4 sentences of plain-language reasoning "
    "about why the score landed where it did and which missing must-have skills "
    "matter most. Never recommend hiring or rejecting the candidate - you explain "
    "the match, you do not decide."
)


def is_configured() -> bool:
    return bool(get_settings().gemini_api_key.strip())


def generate_explanation(score: dict, skills: dict, must_have_skills: list[str], nice_to_have_skills: list[str]) -> dict:
    """Returns {"success": True, "explanation": str} or {"success": False, "error": str}.
    Never falls back to a fake canned explanation.
    """
    settings = get_settings()
    if not settings.gemini_api_key.strip():
        return {"success": False, "error": UNAVAILABLE_MESSAGE}

    try:
        from google import genai
    except ImportError:
        return {"success": False, "error": UNAVAILABLE_MESSAGE}

    user_content = (
        "Candidate score data:\n"
        f"- overall: {score.get('overall')}\n"
        f"- skill_match_pct: {score.get('skill_match_pct')}\n"
        f"- tfidf_similarity: {score.get('tfidf_similarity')}\n"
        f"- embedding_similarity: {score.get('embedding_similarity')}\n"
        f"- weights_used: {score.get('weights_used')}\n\n"
        "Skill comparison:\n"
        f"- matched: {skills.get('matched')}\n"
        f"- missing_must_have: {skills.get('missing_must_have')}\n"
        f"- missing_nice_to_have: {skills.get('missing_nice_to_have')}\n\n"
        f"Job must-have skills: {must_have_skills}\n"
        f"Job nice-to-have skills: {nice_to_have_skills}\n"
    )

    try:
        client = genai.Client(api_key=settings.gemini_api_key)
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=f"{SYSTEM_PROMPT}\n\n{user_content}",
        )
    except Exception as exc:
        logger.warning("Explanation generation failed: %s", exc)
        return {"success": False, "error": UNAVAILABLE_MESSAGE}

    text = (response.text or "").strip()
    if not text:
        return {"success": False, "error": UNAVAILABLE_MESSAGE}

    return {"success": True, "explanation": text}
