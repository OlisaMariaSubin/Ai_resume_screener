from app.services.tfidf_matcher import compute_tfidf_similarities


def test_similar_texts_score_higher_than_unrelated():
    jd_text = "We need a Python backend engineer with FastAPI and PostgreSQL experience."
    similar_resume = "Backend engineer skilled in Python, FastAPI, and PostgreSQL database design."
    unrelated_resume = "Professional chef with ten years of experience in French pastry and baking."

    similarities = compute_tfidf_similarities(jd_text, [similar_resume, unrelated_resume])

    assert similarities[0] > similarities[1]


def test_similarity_bounded_between_zero_and_one():
    similarities = compute_tfidf_similarities("Python developer", ["Python developer role"])
    assert 0.0 <= similarities[0] <= 1.0


def test_empty_resume_list_returns_empty():
    assert compute_tfidf_similarities("Python developer", []) == []
