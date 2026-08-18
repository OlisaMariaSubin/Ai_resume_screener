import logging
import threading

logger = logging.getLogger(__name__)

_model = None
_model_lock = threading.Lock()
_MODEL_NAME = "all-MiniLM-L6-v2"


def _get_model():
    """Lazily load and cache the sentence-transformers model once per process."""
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                from sentence_transformers import SentenceTransformer

                _model = SentenceTransformer(_MODEL_NAME, device="cpu")
    return _model


def is_available() -> bool:
    try:
        _get_model()
        return True
    except Exception as exc:  # model not installed / download failed
        logger.warning("Embedding model unavailable: %s", exc)
        return False


def compute_embedding_similarities(jd_text: str, resume_texts: list[str]) -> list[float] | None:
    """Compute cosine similarity between JD and each resume using sentence embeddings.

    Returns None if the embedding model can't be loaded (caller should treat the
    embedding component as unavailable and fall back to TF-IDF only), never a fake value.
    """
    if not resume_texts:
        return []

    try:
        model = _get_model()
        from sentence_transformers import util

        jd_embedding = model.encode(jd_text, convert_to_tensor=True)
        resume_embeddings = model.encode(resume_texts, convert_to_tensor=True)
        scores = util.cos_sim(jd_embedding, resume_embeddings)[0]
        return [float(max(0.0, min(1.0, s))) for s in scores.tolist()]
    except Exception as exc:
        logger.warning("Embedding similarity computation failed: %s", exc)
        return None
