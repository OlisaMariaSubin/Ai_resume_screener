"""Canonical skill list, alias/normalization map, and JD fairness-language patterns.

This is a maintainable, hand-curated dictionary (not an ML model) so that skill
detection and normalization stay deterministic and explainable.
"""

# Canonical skills, grouped only for readability - the flat set is what's used at runtime.
SKILL_CATEGORIES: dict[str, list[str]] = {
    "languages": [
        "Python", "Java", "C", "C++", "C#", "JavaScript", "TypeScript", "Go", "Rust",
        "Ruby", "PHP", "Swift", "Kotlin", "Scala", "R", "MATLAB", "Perl",
    ],
    "web_frameworks": [
        "React", "Angular", "Vue.js", "Node.js", "FastAPI", "Django", "Flask",
        "Spring Boot", "Express.js", "Next.js", "HTML", "CSS", "REST", "GraphQL",
    ],
    "databases": [
        "SQL", "MySQL", "PostgreSQL", "MongoDB", "SQLite", "Redis", "Oracle",
        "Cassandra", "DynamoDB",
    ],
    "cloud_devops": [
        "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Git", "Linux", "CI/CD",
        "Jenkins", "Terraform", "DevOps", "Ansible", "Nginx",
    ],
    "ml_ai": [
        "Machine Learning", "Deep Learning", "Artificial Intelligence", "NLP",
        "TensorFlow", "PyTorch", "scikit-learn", "Pandas", "NumPy", "Computer Vision",
        "Data Science", "Keras", "OpenCV",
    ],
    "other": [
        "Cybersecurity", "Agile", "Scrum", "Project Management", "Microservices",
        "System Design", "Testing", "QA",
    ],
}

ALL_SKILLS: list[str] = [skill for group in SKILL_CATEGORIES.values() for skill in group]

# Map alias (lowercase) -> canonical skill name.
SKILL_ALIASES: dict[str, str] = {
    "js": "JavaScript",
    "ts": "TypeScript",
    "reactjs": "React",
    "react.js": "React",
    "node": "Node.js",
    "nodejs": "Node.js",
    "postgres": "PostgreSQL",
    "postgressql": "PostgreSQL",
    "ml": "Machine Learning",
    "dl": "Deep Learning",
    "ai": "Artificial Intelligence",
    "k8s": "Kubernetes",
    "golang": "Go",
    "c plus plus": "C++",
    "cpp": "C++",
    "csharp": "C#",
    "c sharp": "C#",
    "vue": "Vue.js",
    "vuejs": "Vue.js",
    "expressjs": "Express.js",
    "express": "Express.js",
    "nextjs": "Next.js",
    "sklearn": "scikit-learn",
    "scikit learn": "scikit-learn",
    "tensor flow": "TensorFlow",
    "py torch": "PyTorch",
    "cv": "Computer Vision",
    "nlp": "NLP",
    "sql server": "SQL",
    "mongo": "MongoDB",
    "gcp": "GCP",
    "google cloud": "GCP",
    "google cloud platform": "GCP",
    "amazon web services": "AWS",
    "microsoft azure": "Azure",
    "ci cd": "CI/CD",
    "cicd": "CI/CD",
    "spring": "Spring Boot",
    "springboot": "Spring Boot",
}


def canonical_skill_name(raw: str) -> str:
    """Resolve a raw skill mention to its canonical display name."""
    key = raw.strip().lower()
    if key in SKILL_ALIASES:
        return SKILL_ALIASES[key]
    for skill in ALL_SKILLS:
        if skill.lower() == key:
            return skill
    return raw.strip()


# JD fairness language scan (Section 9.3). Deterministic keyword/pattern list, not an
# LLM guess. category groups let the UI show *why* something was flagged.
FAIRNESS_PATTERNS: dict[str, list[str]] = {
    "gendered_language": [
        "he/she", "his/her", "himself/herself", "chairman", "manpower", "salesman",
        "he or she", "waiter", "waitress", "policeman", "policewoman",
    ],
    "ageist_language": [
        "young and energetic", "digital native", "recent graduate only",
        "youthful", "young team", "energetic young", "under 30", "young professional",
    ],
    "exclusionary_requirements": [
        "native english speaker", "native speaker", "no accent", "perfect english",
        "must be a us citizen", "no visa sponsorship", "local candidates only",
    ],
    "ableist_language": [
        "able-bodied", "must be able to stand for long periods without accommodation",
        "physically fit", "no health issues",
    ],
}
