"""
jd_parser.py — Auto-extract structured requirements from a raw Job Description.

Returns:
  skills      : list of tech/domain skills found in the JD
  experience_years : minimum years of experience required (int or None)
  education   : highest required degree label (str or None)
  seniority   : "junior" | "mid" | "senior" | "lead" | "principal" | None
"""

import re
from typing import Dict, Any, List, Optional

# ---------------------------------------------------------------------------
# Curated tech / domain vocabulary (~300 terms).
# Skills are matched case-insensitively as whole words.
# ---------------------------------------------------------------------------
TECH_VOCAB = sorted([
    # Languages
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "golang",
    "rust", "kotlin", "swift", "scala", "ruby", "php", "r", "matlab", "julia",
    "perl", "bash", "shell", "powershell", "groovy",
    # Web
    "html", "css", "react", "react.js", "reactjs", "vue", "vue.js", "vuejs",
    "angular", "next.js", "nextjs", "nuxt", "svelte", "node.js", "nodejs",
    "express", "fastapi", "flask", "django", "spring", "spring boot",
    "asp.net", ".net", "rails", "laravel", "graphql", "rest", "restful",
    "websocket", "webpack", "vite", "tailwind", "bootstrap", "sass",
    # Data / ML / AI
    "machine learning", "deep learning", "natural language processing", "nlp",
    "computer vision", "cv", "reinforcement learning", "data science",
    "data analysis", "data engineering", "feature engineering",
    "tensorflow", "pytorch", "keras", "scikit-learn", "sklearn",
    "huggingface", "transformers", "bert", "gpt", "llm", "rag",
    "langchain", "openai", "anthropic", "xgboost", "lightgbm",
    "pandas", "numpy", "scipy", "matplotlib", "seaborn", "plotly",
    "opencv", "pillow",
    # Databases
    "sql", "mysql", "postgresql", "postgres", "sqlite", "oracle", "sql server",
    "mongodb", "cassandra", "redis", "elasticsearch", "dynamodb",
    "neo4j", "influxdb", "clickhouse", "snowflake", "redshift", "bigquery",
    "hive", "hbase", "couchdb", "firebase",
    # Cloud & DevOps
    "aws", "azure", "gcp", "google cloud",
    "ec2", "s3", "lambda", "ecs", "eks", "fargate", "rds", "sqs", "sns",
    "docker", "kubernetes", "k8s", "helm", "terraform", "ansible",
    "jenkins", "github actions", "gitlab ci", "circleci", "travis ci",
    "ci/cd", "devops", "sre", "linux", "unix", "nginx", "apache",
    "prometheus", "grafana", "datadog", "splunk",
    # Data pipeline / Big data
    "spark", "apache spark", "hadoop", "kafka", "apache kafka", "flink",
    "airflow", "apache airflow", "dbt", "prefect", "luigi", "databricks",
    # Tools & practices
    "git", "github", "gitlab", "bitbucket", "jira", "confluence",
    "agile", "scrum", "kanban", "tdd", "bdd", "microservices",
    "api", "sdk", "orm", "jwt", "oauth", "grpc", "protobuf",
    # Mobile
    "android", "ios", "react native", "flutter", "xamarin",
    # Security
    "cybersecurity", "penetration testing", "owasp", "siem", "iam",
    # BI / Analytics
    "tableau", "power bi", "looker", "qlik", "dax", "excel",
    # Other common
    "figma", "photoshop", "ux", "ui", "product management",
], key=len, reverse=True)  # longest-first so multi-word terms match before substrings

# ---------------------------------------------------------------------------
# Seniority level vocabulary
# ---------------------------------------------------------------------------
SENIORITY_MAP = {
    "intern":    "intern",
    "internship":"intern",
    "fresher":   "junior",
    "entry level":"junior",
    "entry-level":"junior",
    "junior":    "junior",
    "associate": "junior",
    "mid level": "mid",
    "mid-level": "mid",
    "mid senior":"senior",
    "senior":    "senior",
    "sr.":       "senior",
    "sr ":       "senior",
    "staff":     "senior",
    "lead":      "lead",
    "tech lead": "lead",
    "principal": "principal",
    "architect": "principal",
    "manager":   "lead",
    "director":  "principal",
    "head of":   "principal",
    "vp":        "principal",
}

SENIORITY_ORDER = ["intern", "junior", "mid", "senior", "lead", "principal"]

# Education degree mapping (same as ranker)
DEGREE_LEVELS = {
    "phd": 5, "ph.d": 5, "doctorate": 5, "doctoral": 5,
    "masters": 4, "master": 4, "m.tech": 4, "m.s": 4, "mtech": 4,
    "m.e": 4, "mba": 4, "m.sc": 4, "msc": 4, "m.b.a": 4,
    "bachelors": 3, "bachelor": 3, "b.tech": 3, "b.e": 3, "btech": 3,
    "b.sc": 3, "bsc": 3, "b.s": 3, "undergraduate": 3,
    "diploma": 2, "polytechnic": 2,
    "12th": 1, "hsc": 1, "high school": 1,
}

# Friendly labels for display
DEGREE_LABEL = {
    5: "PhD / Doctorate",
    4: "Masters",
    3: "Bachelors",
    2: "Diploma",
    1: "High School",
}


def parse_jd(jd_text: str) -> Dict[str, Any]:
    """
    Parse a free-form job description string and extract structured requirements.

    Returns:
        {
            "skills":            ["Python", "SQL", "AWS", ...],
            "experience_years":  5,          # or None
            "education":         "Bachelors", # or None
            "seniority":         "Senior",   # or None
        }
    """
    text_lower = jd_text.lower()

    return {
        "skills":           _extract_skills(jd_text, text_lower),
        "experience_years": _extract_experience(text_lower),
        "education":        _extract_education(text_lower),
        "seniority":        _extract_seniority(text_lower),
    }


# ---------------------------------------------------------------------------
# Skills extraction
# ---------------------------------------------------------------------------

def _extract_skills(original: str, text_lower: str) -> List[str]:
    """
    Match tech vocabulary terms against the JD (whole-word, case-insensitive).
    Preserves original casing from the vocab list.
    """
    found: List[str] = []
    consumed_spans = []

    for term in TECH_VOCAB:
        # Build a word-boundary-aware pattern
        pattern = r"(?<![a-zA-Z0-9+#.])" + re.escape(term) + r"(?![a-zA-Z0-9+#.])"
        for m in re.finditer(pattern, text_lower):
            start, end = m.start(), m.end()
            # Skip if already matched by a longer term
            if any(cs <= start and ce >= end for cs, ce in consumed_spans):
                continue
            consumed_spans.append((start, end))
            # Use pretty-cased version of the term
            found.append(_pretty_case(term))
            break  # only count each vocab term once

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for s in found:
        key = s.lower()
        if key not in seen:
            seen.add(key)
            unique.append(s)

    return unique


def _pretty_case(term: str) -> str:
    """Capitalise acronyms, title-case the rest."""
    ALWAYS_UPPER = {
        "sql", "html", "css", "api", "aws", "gcp", "ux", "ui", "nlp", "cv",
        "tdd", "bdd", "sdk", "orm", "jwt", "sre", "iam", "ci/cd", "rest",
        "grpc", "vp", "hsc", "php",
    }
    ALWAYS_AS_IS = {
        "python": "Python", "javascript": "JavaScript", "typescript": "TypeScript",
        "c++": "C++", "c#": "C#", "go": "Go", "rust": "Rust",
        "react.js": "React.js", "reactjs": "React", "vue.js": "Vue.js",
        "next.js": "Next.js", "node.js": "Node.js", "asp.net": "ASP.NET",
        ".net": ".NET", "tensorflow": "TensorFlow", "pytorch": "PyTorch",
        "scikit-learn": "Scikit-learn", "huggingface": "HuggingFace",
        "langchain": "LangChain", "openai": "OpenAI", "xgboost": "XGBoost",
        "lightgbm": "LightGBM", "mongodb": "MongoDB", "postgresql": "PostgreSQL",
        "elasticsearch": "Elasticsearch", "dynamodb": "DynamoDB",
        "clickhouse": "ClickHouse", "github": "GitHub", "gitlab": "GitLab",
        "bitbucket": "Bitbucket", "jenkins": "Jenkins", "kubernetes": "Kubernetes",
        "terraform": "Terraform", "ansible": "Ansible", "prometheus": "Prometheus",
        "grafana": "Grafana", "datadog": "Datadog", "databricks": "Databricks",
        "kafka": "Kafka", "airflow": "Airflow", "github actions": "GitHub Actions",
        "gitlab ci": "GitLab CI", "circleci": "CircleCI",
        "spring boot": "Spring Boot", "fastapi": "FastAPI",
        "graphql": "GraphQL", "websocket": "WebSocket",
        "machine learning": "Machine Learning", "deep learning": "Deep Learning",
        "natural language processing": "NLP",
        "computer vision": "Computer Vision",
        "data science": "Data Science", "data engineering": "Data Engineering",
        "react native": "React Native",
        "power bi": "Power BI",
        "apache spark": "Apache Spark",
        "apache kafka": "Apache Kafka",
        "apache airflow": "Apache Airflow",
    }
    t = term.lower()
    if t in ALWAYS_AS_IS:
        return ALWAYS_AS_IS[t]
    if t in ALWAYS_UPPER:
        return t.upper()
    # Title-case multi-word, capitalize single word
    return " ".join(w.capitalize() for w in term.split())


# ---------------------------------------------------------------------------
# Experience extraction
# ---------------------------------------------------------------------------

def _extract_experience(text_lower: str) -> Optional[int]:
    """
    Find minimum years-of-experience from phrases like:
    "5+ years", "3-5 years", "minimum 4 years", "at least 2 years"
    Returns the smallest (most lenient) number found, as an int.
    """
    candidates = []

    # "X-Y years" → take lower bound (X)
    for m in re.finditer(r"(\d+)\s*[-–]\s*(\d+)\s*(?:\+?\s*)?years?", text_lower):
        candidates.append(int(m.group(1)))

    # "X+ years" / "X years" / "at least X" / "minimum X"
    patterns = [
        r"(\d+)\s*\+\s*years?",
        r"minimum\s+of\s+(\d+)\s+years?",
        r"minimum\s+(\d+)\s+years?",
        r"at\s+least\s+(\d+)\s+years?",
        r"(\d+)\s+years?\s+of\s+(?:experience|work)",
        r"(\d+)\s+years?\s+(?:relevant|professional|industry)",
        r"(\d+)\+?\s+yrs?",
    ]
    for pat in patterns:
        for m in re.finditer(pat, text_lower):
            val = int(m.group(1))
            if 0 < val < 40:  # sanity filter
                candidates.append(val)

    if not candidates:
        return None
    return min(candidates)  # return the minimum requirement


# ---------------------------------------------------------------------------
# Education extraction
# ---------------------------------------------------------------------------

def _extract_education(text_lower: str) -> Optional[str]:
    """Return the highest degree level mentioned in the JD."""
    best_level = 0

    for keyword, level in DEGREE_LEVELS.items():
        pattern = r"(?<![a-z])" + re.escape(keyword) + r"(?![a-z])"
        if re.search(pattern, text_lower) and level > best_level:
            best_level = level

    return DEGREE_LABEL.get(best_level)


# ---------------------------------------------------------------------------
# Seniority extraction
# ---------------------------------------------------------------------------

def _extract_seniority(text_lower: str) -> Optional[str]:
    """Detect the required seniority level from the JD."""
    detected = []

    for keyword, level in SENIORITY_MAP.items():
        if keyword in text_lower:
            detected.append(level)

    if not detected:
        return None

    # Return the highest seniority mentioned
    for lvl in reversed(SENIORITY_ORDER):
        if lvl in detected:
            return lvl.capitalize()

    return detected[-1].capitalize()
