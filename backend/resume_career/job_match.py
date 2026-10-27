"""Compare a resume with a job description."""

import re
from collections import Counter

from .analyzer import find_skills, learning_step
from .skills_data import STOPWORDS

TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z+#.\-]{2,}")
MIN_JD_CHARS = 40


def _keywords(text, limit=25):
    """Most frequent meaningful single words in `text` (lower-cased)."""
    words = [w.lower().strip(".-") for w in TOKEN_RE.findall(text)]
    words = [w for w in words if w not in STOPWORDS and len(w) >= 3]
    return [w for w, _ in Counter(words).most_common(limit)]


def match_job(resume_text, job_description, job_title=""):
    jd_skills = find_skills(job_description)
    resume_skills = find_skills(resume_text)

    matched = sorted(s for s in jd_skills if s in resume_skills)
    missing = sorted(s for s in jd_skills if s not in resume_skills)

    resume_words = set(w.lower().strip(".-") for w in TOKEN_RE.findall(resume_text))
    jd_keywords = _keywords(job_description)
    skill_words = {w.lower() for s in jd_skills for w in s.split()}
    other_keywords = [k for k in jd_keywords if k not in skill_words]
    kw_matched = [k for k in other_keywords if k in resume_words]
    kw_missing = [k for k in other_keywords if k not in resume_words][:10]

    skill_pct = round(100 * len(matched) / len(jd_skills), 1) if jd_skills else None
    kw_pct = round(100 * len(kw_matched) / len(other_keywords), 1) if other_keywords else 0.0

    if skill_pct is None:
        score = kw_pct
    else:
        score = round(0.7 * skill_pct + 0.3 * kw_pct, 1)

    suggestions = []
    if missing:
        suggestions.append(
            "The job asks for " + ", ".join(missing[:8]) + " but they were not found in your resume. "
            "Add them only if you genuinely have the experience, ideally inside a project or experience bullet, not just a list."
        )
    if kw_missing:
        suggestions.append(
            "Consider mirroring important wording from the posting where it is accurate: " + ", ".join(kw_missing[:8]) + "."
        )
    if matched and score < 60:
        suggestions.append("Move your matching skills and most relevant projects higher on the page so they are seen first.")
    if score >= 75:
        suggestions.append("Strong match. Tailor your summary to this role and make sure the matching skills appear in recent bullets.")
    if not jd_skills:
        suggestions.append("No standard technical skills were recognised in this job description, so the score is based on general keyword overlap only.")

    return {
        "job_title": job_title.strip() or None,
        "match_score": score,
        "skill_match_percent": skill_pct,
        "keyword_overlap_percent": kw_pct,
        "required_skills": sorted(jd_skills),
        "matched_skills": matched,
        "missing_skills": missing,
        "missing_keywords": kw_missing,
        "learning_plan": [learning_step(s) for s in missing[:5]],
        "suggestions": suggestions,
    }
