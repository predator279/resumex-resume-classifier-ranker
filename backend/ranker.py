"""
ranker.py — 5-dimension ATS scoring engine.

Dimensions & weights:
  1. Keyword / Skills Match   35%  (frequency-weighted, not just boolean)
  2. Semantic Match           20%  (MiniLM cosine similarity)
  3. Experience Match         25%  (years + work-history date detection)
  4. Education Match          10%  (degree level comparison)
  5. Seniority Fit            10%  (title-level match vs JD seniority)

Hard rules:
  - skills_score < 0.25  → cap final at 45
  - seniority mismatch (e.g. Junior for Senior role) → cap final at 60
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from .models_loader import get_sentence_transformer
from .file_parser import extract_text, clean_text
from .jd_parser import DEGREE_LEVELS, DEGREE_LABEL, SENIORITY_ORDER

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Seniority mapping for resumes (job-title detection)
# ---------------------------------------------------------------------------
RESUME_SENIORITY_SIGNALS = {
    "intern":       "intern",
    "trainee":      "intern",
    "fresher":      "junior",
    "junior":       "junior",
    "associate":    "junior",
    "entry level":  "junior",
    "entry-level":  "junior",
    "mid level":    "mid",
    "mid-level":    "mid",
    "ii":           "mid",      # "Software Engineer II"
    "iii":          "senior",
    "senior":       "senior",
    "sr.":          "senior",
    "sr ":          "senior",
    "staff":        "senior",
    "lead":         "lead",
    "principal":    "principal",
    "architect":    "principal",
    "manager":      "lead",
    "director":     "principal",
    "head of":      "principal",
    "vp":           "principal",
    "vice president": "principal",
}

STEM_KEYWORDS = [
    "computer science", "information technology", "software", "engineering",
    "electronics", "electrical", "data science", "artificial intelligence",
    "machine learning", "mathematics", "statistics", "cs", "it", "cse", "ece",
]

# ---------------------------------------------------------------------------
# 1. Keyword / Skills scoring  (35%)
# ---------------------------------------------------------------------------

def _score_keywords(resume_text: str, required_skills: List[str]) -> Dict[str, Any]:
    """
    Frequency-weighted keyword matching.

    For each required skill:
      - Count occurrences in resume text
      - 0 occurrences  → 0.0
      - 1 occurrence   → 0.7  (mentioned)
      - 2+ occurrences → 1.0  (prominent)

    Score = weighted_sum / len(required_skills)
    Also tracks matched / missing for display.
    """
    if not required_skills:
        return {
            "score": 0.5,
            "matched": [],
            "missing": [],
            "note": "No skills specified",
        }

    resume_lower = resume_text.lower()
    matched, missing = [], []
    total = 0.0

    for skill in required_skills:
        pattern = r"(?<![a-zA-Z0-9+#.])" + re.escape(skill.lower()) + r"(?![a-zA-Z0-9+#.])"
        count = len(re.findall(pattern, resume_lower))
        if count >= 2:
            total += 1.0
            matched.append(skill)
        elif count == 1:
            total += 0.7
            matched.append(skill)
        else:
            total += 0.0
            missing.append(skill)

    score = total / len(required_skills)
    return {
        "score": round(score, 4),
        "matched": matched,
        "missing": missing,
    }


# ---------------------------------------------------------------------------
# 2. Semantic Match  (20%)
# ---------------------------------------------------------------------------

def _score_semantic(resume_text: str, jd_text: str) -> Dict[str, Any]:
    """MiniLM cosine similarity between resume and full JD text."""
    if not jd_text.strip():
        return {"score": 0.5, "note": "No JD text for semantic match"}

    st = get_sentence_transformer()
    embeddings = st.encode(
        [resume_text[:3000], jd_text[:3000]],
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    sim = float(cosine_similarity([embeddings[0]], [embeddings[1]])[0][0])
    sim = max(0.0, min(1.0, sim))
    return {"score": round(sim, 4)}


# ---------------------------------------------------------------------------
# 3. Experience Match  (25%)
# ---------------------------------------------------------------------------

def _extract_years_from_text(text: str) -> Optional[float]:
    """Find the largest years-of-experience value mentioned in text."""
    t = text.lower()
    candidates = []

    # Date ranges like "2019 – 2024" → ~5 years (work history)
    for m in re.finditer(
        r"(\d{4})\s*[-–—]\s*((?:\d{4}|present|current|now|till date))",
        t,
    ):
        start_yr = int(m.group(1))
        end_raw = m.group(2).strip()
        if end_raw.isdigit():
            end_yr = int(end_raw)
        else:
            end_yr = 2025  # treat "present" as current year
        diff = end_yr - start_yr
        if 0 < diff < 50:
            candidates.append(float(diff))

    # Explicit "X years" statements
    for pat in [
        r"(\d+(?:\.\d+)?)\s*\+?\s*years?",
        r"(\d+(?:\.\d+)?)\s*\+?\s*yrs?",
    ]:
        for m in re.finditer(pat, t):
            val = float(m.group(1))
            if 0 < val < 50:
                candidates.append(val)

    # "X-Y years" → take upper bound (candidate's claim)
    for m in re.finditer(r"(\d+)\s*-\s*(\d+)\s*years?", t):
        candidates.append(float(m.group(2)))

    return max(candidates) if candidates else None


def _score_experience(
    resume_text: str,
    required_years: Optional[int],
) -> Dict[str, Any]:
    detected = _extract_years_from_text(resume_text)

    if required_years is None:
        return {
            "score": 0.5,
            "detected_years": detected,
            "required_years": None,
            "note": "No experience requirement",
        }

    if detected is None:
        score = 0.3
    elif detected >= required_years:
        score = 1.0
    elif detected >= required_years - 1:
        score = 0.7
    elif detected >= required_years - 2:
        score = 0.4
    else:
        score = 0.2

    return {
        "score": round(score, 4),
        "detected_years": round(detected, 1) if detected else None,
        "required_years": required_years,
    }


# ---------------------------------------------------------------------------
# 4. Education Match  (10%)
# ---------------------------------------------------------------------------

def _detect_degree_level(text: str) -> Tuple[int, str]:
    t = text.lower()
    best_level, best_label = 0, "Not detected"
    for kw, level in DEGREE_LEVELS.items():
        if re.search(r"(?<![a-z])" + re.escape(kw) + r"(?![a-z])", t) and level > best_level:
            best_level = level
            best_label = DEGREE_LABEL.get(level, kw)
    return best_level, best_label


def _score_education(
    resume_text: str,
    required_education: Optional[str],
) -> Dict[str, Any]:
    detected_level, detected_label = _detect_degree_level(resume_text)

    if not required_education:
        return {
            "score": 0.5,
            "detected": detected_label,
            "required": "Not specified",
            "note": "No education requirement",
        }

    req_level, req_label = _detect_degree_level(required_education)

    if req_level == 0:
        return {
            "score": 0.5,
            "detected": detected_label,
            "required": req_label,
            "note": "Could not parse education requirement",
        }

    if detected_level == 0:
        score = 0.2
    elif detected_level >= req_level:
        score = 1.0
    elif detected_level == req_level - 1:
        score = 0.6
    else:
        score = 0.2

    # STEM field bonus
    resume_lower, ed_lower = resume_text.lower(), required_education.lower()
    if any(kw in resume_lower for kw in STEM_KEYWORDS) and any(
        kw in ed_lower for kw in STEM_KEYWORDS
    ):
        score = min(1.0, score + 0.1)

    return {
        "score": round(score, 4),
        "detected": detected_label,
        "required": req_label,
    }


# ---------------------------------------------------------------------------
# 5. Seniority Fit  (10%)
# ---------------------------------------------------------------------------

def _detect_resume_seniority(resume_text: str) -> Optional[str]:
    t = resume_text.lower()
    detected = []
    for kw, level in RESUME_SENIORITY_SIGNALS.items():
        if kw in t:
            detected.append(level)
    if not detected:
        return None
    # Return highest level detected
    for lvl in reversed(SENIORITY_ORDER):
        if lvl in detected:
            return lvl
    return detected[-1]


def _score_seniority(
    resume_text: str,
    required_seniority: Optional[str],
) -> Dict[str, Any]:
    detected_raw = _detect_resume_seniority(resume_text)
    detected = detected_raw.lower() if detected_raw else None

    required = required_seniority.lower() if required_seniority else None

    if not required:
        return {
            "score": 0.7,  # neutral-positive when JD doesn't specify
            "detected": detected_raw.capitalize() if detected_raw else "Not detected",
            "required": "Not specified",
            "note": "No seniority requirement",
        }

    if not detected:
        score = 0.4  # candidate didn't signal level clearly
    else:
        req_idx = SENIORITY_ORDER.index(required) if required in SENIORITY_ORDER else 2
        det_idx = SENIORITY_ORDER.index(detected) if detected in SENIORITY_ORDER else 2
        gap = det_idx - req_idx

        if gap == 0:
            score = 1.0       # exact match
        elif gap == 1:
            score = 0.85      # one level above (overqualified — acceptable)
        elif gap == -1:
            score = 0.55      # one level below (borderline)
        elif gap >= 2:
            score = 0.8       # significantly overqualified
        else:
            score = 0.2       # significantly underqualified

    mismatch = (
        required in ("senior", "lead", "principal")
        and detected in ("intern", "junior")
    )

    return {
        "score": round(score, 4),
        "detected": detected_raw.capitalize() if detected_raw else "Not detected",
        "required": required_seniority.capitalize() if required_seniority else "Not specified",
        "mismatch": mismatch,
    }


# ---------------------------------------------------------------------------
# Recruiter insight note
# ---------------------------------------------------------------------------

def _recruiter_note(
    final_score: float,
    skills_result: Dict,
    seniority_result: Dict,
    experience_result: Dict,
) -> str:
    missing = skills_result.get("missing", [])
    seniority_mismatch = seniority_result.get("mismatch", False)
    det_yrs = experience_result.get("detected_years")
    req_yrs = experience_result.get("required_years")
    under_exp = req_yrs and det_yrs and det_yrs < req_yrs - 1

    if final_score >= 80:
        note = "Strong match · Recommend for interview"
        if missing:
            note += f" · Gap: {', '.join(missing[:2])}"
    elif final_score >= 65:
        note = "Good match · Review gaps before decision"
        if missing:
            note += f" · Missing: {', '.join(missing[:3])}"
    elif final_score >= 45:
        note = "Partial match · Significant gaps exist"
        if seniority_mismatch:
            note += " · Seniority level too low"
        elif under_exp:
            note += f" · Under-experienced ({det_yrs}y vs {req_yrs}y required)"
        elif missing:
            note += f" · Missing: {', '.join(missing[:3])}"
    else:
        note = "Weak match · Does not meet core requirements"
        if missing:
            note += f" · Critical missing: {', '.join(missing[:4])}"

    return note


# ---------------------------------------------------------------------------
# Main ranking function
# ---------------------------------------------------------------------------

def rank_resumes(
    files: List[Tuple[str, bytes]],
    jd_text: str,
    required_skills: List[str],
    required_years: Optional[int],
    required_education: Optional[str],
    required_seniority: Optional[str],
) -> Dict[str, Any]:
    """
    Score and rank a list of (filename, bytes) tuples against the parsed JD.

    Args:
        files:               list of (filename, raw_bytes)
        jd_text:             full JD text (used for semantic embedding)
        required_skills:     list of skill strings (from parser or user override)
        required_years:      minimum years experience (int or None)
        required_education:  education requirement string or None
        required_seniority:  seniority level string or None

    Returns:
        {"ranked": [...], "jd_parsed": {...}}
    """
    results = []

    for filename, file_bytes in files:
        raw = extract_text(filename, file_bytes)
        text = clean_text(raw)

        if not text:
            results.append({
                "filename": filename,
                "final_score": 0.0,
                "breakdown": {},
                "recruiter_note": "Could not extract text from file.",
                "error": True,
            })
            continue

        kw_result  = _score_keywords(text, required_skills)
        sem_result = _score_semantic(text, jd_text)
        exp_result = _score_experience(text, required_years)
        edu_result = _score_education(text, required_education)
        sen_result = _score_seniority(text, required_seniority)

        kw  = kw_result["score"]
        sem = sem_result["score"]
        exp = exp_result["score"]
        edu = edu_result["score"]
        sen = sen_result["score"]

        final = (0.35 * kw + 0.20 * sem + 0.25 * exp + 0.10 * edu + 0.10 * sen) * 100

        # Hard caps
        if kw < 0.25:
            final = min(final, 45)
        if sen_result.get("mismatch"):
            final = min(final, 60)

        note = _recruiter_note(final, kw_result, sen_result, exp_result)

        results.append({
            "filename": filename,
            "final_score": round(final, 1),
            "recruiter_note": note,
            "breakdown": {
                "keywords": kw_result,
                "semantic":  sem_result,
                "experience": exp_result,
                "education": edu_result,
                "seniority": sen_result,
            },
        })

    results.sort(key=lambda x: x["final_score"], reverse=True)
    for i, r in enumerate(results, start=1):
        r["rank"] = i

    return {
        "ranked": results,
        "weights": {
            "keywords": 0.35,
            "semantic":  0.20,
            "experience": 0.25,
            "education": 0.10,
            "seniority": 0.10,
        },
    }
