from app.services.skill_extractor import extract_skills_from_text


def test_extracts_known_skills():
    skills = extract_skills_from_text("Experienced in Python, FastAPI, and PostgreSQL.")
    assert "Python" in skills
    assert "FastAPI" in skills
    assert "PostgreSQL" in skills


def test_alias_js_normalizes_to_javascript():
    skills = extract_skills_from_text("Strong JS skills")
    assert "JavaScript" in skills
    assert "JS" not in skills


def test_alias_ml_normalizes_to_machine_learning():
    skills = extract_skills_from_text("Worked on ML pipelines")
    assert "Machine Learning" in skills


def test_alias_k8s_normalizes_to_kubernetes():
    skills = extract_skills_from_text("Deployed services with K8s")
    assert "Kubernetes" in skills


def test_no_duplicate_skills():
    skills = extract_skills_from_text("Python and python and PYTHON")
    assert skills.count("Python") == 1


def test_no_skills_in_unrelated_text():
    skills = extract_skills_from_text("The quick brown fox jumps over the lazy dog")
    assert skills == []
