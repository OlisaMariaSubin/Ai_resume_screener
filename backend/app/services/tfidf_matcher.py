from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def compute_tfidf_similarities(jd_text: str, resume_texts: list[str]) -> list[float]:
    """Compute TF-IDF cosine similarity between a JD and each resume text.

    Fits the vectorizer across the JD + all resumes in the batch so IDF weighting
    reflects the actual applicant pool (falls back gracefully for a single resume).
    Returns a similarity in [0, 1] per resume, in the same order as resume_texts.
    """
    if not resume_texts:
        return []

    corpus = [jd_text] + resume_texts
    vectorizer = TfidfVectorizer(stop_words="english", lowercase=True, max_features=5000)

    try:
        matrix = vectorizer.fit_transform(corpus)
    except ValueError:
        # Empty vocabulary (e.g. all-stopword or empty texts) - no signal, similarity 0.
        return [0.0] * len(resume_texts)

    jd_vector = matrix[0:1]
    resume_vectors = matrix[1:]
    similarities = cosine_similarity(jd_vector, resume_vectors)[0]
    return [float(max(0.0, min(1.0, s))) for s in similarities]


def compute_tfidf_similarity(jd_text: str, resume_text: str) -> float:
    return compute_tfidf_similarities(jd_text, [resume_text])[0]
