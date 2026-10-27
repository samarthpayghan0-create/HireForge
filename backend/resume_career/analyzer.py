"""Rule-based resume analysis. Deterministic, needs no API key."""

import re

from .skills_data import (
    ACTION_VERBS, LEARNING_HINTS, ROLES, SECTION_PATTERNS, SKILLS, SKILL_PATTERNS, STRICT_ALIASES,
)

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d{1,3}[\s-]?)?(?:\(?\d{3,5}\)?[\s-]?)?\d{3,5}[\s-]?\d{4,5}(?!\d)")
LINKEDIN_RE = re.compile(r"linkedin\.com/in/[\w-]+|linkedin", re.IGNORECASE)
GITHUB_RE = re.compile(r"github\.com/[\w-]+|github", re.IGNORECASE)
NUMBER_RE = re.compile(r"\d+\s?%|\d+[\d,.]*\s?(?:\+|k\b|x\b|users|requests|records|students|customers|ms\b)|\b\d{2,}\b")
BULLET_RE = re.compile(r"^\s*(?:[-•*●▪◦–·]|\d+[.)])\s+")
FIRST_PERSON_RE = re.compile(r"\b(i am|i have|i was|i worked|my name|i\b)", re.IGNORECASE)

WEIGHTS = {
    "contact": 15,
    "sections": 25,
    "skills_keywords": 20,
    "length": 10,
    "bullets_action": 15,
    "quantified": 10,
    "language": 5,
}  # sums to 100


def find_skills(text):
    """Return {canonical_skill: category} for skills present in `text`."""
    found = {}
    lowered = text
    for skill, patterns in SKILL_PATTERNS.items():
        aliases = SKILLS[skill][1]
        for alias, pattern in zip(aliases, patterns):
            if skill in STRICT_ALIASES and alias.lower() != skill.lower() and len(alias) <= 3:
                # very short ambiguous aliases (ml, qa, rest) only count in a skills-style context
                if not re.search(r"(skills|technologies|tools)[^\n]{0,200}" + re.escape(alias), lowered, re.IGNORECASE):
                    continue
            if skill in {"Go", "C", "R"}:
                # require capitalised standalone token in a list-like context
                if not re.search(r"(?:^|[,;:|/•\n]\s*)" + re.escape(skill) + r"\s*(?:[,;|/\n]|$)", text):
                    continue
                found[skill] = SKILLS[skill][0]
                break
            if pattern.search(text):
                found[skill] = SKILLS[skill][0]
                break
    return found


def detect_sections(text):
    present = []
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    for name, pattern in SECTION_PATTERNS.items():
        regex = re.compile(pattern, re.IGNORECASE)
        for line in lines:
            # headings are short lines
            if len(line) <= 60 and regex.search(line):
                present.append(name)
                break
    return present


def _stats(text):
    lines = [l for l in text.split("\n") if l.strip()]
    words = re.findall(r"[A-Za-z0-9+#.'/-]+", text)
    bullets = [l for l in lines if BULLET_RE.match(l)]
    candidate_lines = bullets or [l for l in lines if len(l.split()) >= 5]
    action = 0
    for line in candidate_lines:
        stripped = BULLET_RE.sub("", line).strip()
        first = re.match(r"[A-Za-z]+", stripped)
        if first and first.group(0).lower() in ACTION_VERBS:
            action += 1
    quantified = sum(1 for l in lines if NUMBER_RE.search(l) and len(l.split()) >= 4)
    return {
        "word_count": len(words),
        "line_count": len(lines),
        "bullet_count": len(bullets),
        "action_verb_lines": action,
        "quantified_lines": quantified,
        "first_person_count": len(FIRST_PERSON_RE.findall(text)),
    }


def _pct(points, weight):
    return round(max(0.0, min(1.0, points)) * weight, 1)


def score_resume(text, sections, skills, stats, contact):
    b = {}
    b["contact"] = _pct(
        (contact["email"] * 0.4) + (contact["phone"] * 0.3) + ((contact["linkedin"] or contact["github"]) * 0.3),
        WEIGHTS["contact"],
    )
    core_sections = ["Education", "Skills", "Projects", "Experience"]
    sec_points = sum(0.2 for s in core_sections if s in sections)
    sec_points += 0.1 if "Summary / Objective" in sections else 0
    sec_points += 0.1 if ("Certifications" in sections or "Achievements" in sections) else 0
    b["sections"] = _pct(sec_points, WEIGHTS["sections"])
    b["skills_keywords"] = _pct(len(skills) / 12, WEIGHTS["skills_keywords"])
    wc = stats["word_count"]
    if 300 <= wc <= 900:
        length = 1.0
    elif wc < 300:
        length = wc / 300
    else:
        length = max(0.4, 1 - (wc - 900) / 1500)
    b["length"] = _pct(length, WEIGHTS["length"])
    bullet_part = min(stats["bullet_count"] / 8, 1) * 0.5
    verb_part = min(stats["action_verb_lines"] / 6, 1) * 0.5
    b["bullets_action"] = _pct(bullet_part + verb_part, WEIGHTS["bullets_action"])
    b["quantified"] = _pct(stats["quantified_lines"] / 4, WEIGHTS["quantified"])
    b["language"] = _pct(1.0 if stats["first_person_count"] <= 1 else 0.4, WEIGHTS["language"])
    overall = round(sum(b.values()), 1)
    ats = round(
        (b["contact"] + b["sections"] + b["skills_keywords"] + b["length"]) / (
            WEIGHTS["contact"] + WEIGHTS["sections"] + WEIGHTS["skills_keywords"] + WEIGHTS["length"]
        ) * 100, 1,
    )
    return overall, ats, b


def build_feedback(text, sections, skills, stats, contact):
    strengths, improvements = [], []

    def add(priority, message):
        improvements.append({"priority": priority, "text": message})

    if contact["email"] and contact["phone"]:
        strengths.append("Email and phone number are present, so recruiters and ATS can contact you.")
    if not contact["email"]:
        add("high", "Add a professional email address at the top of your resume.")
    if not contact["phone"]:
        add("high", "Add a phone number at the top of your resume.")
    if not (contact["linkedin"] or contact["github"]):
        add("medium", "Add your LinkedIn and/or GitHub profile link so employers can see your work.")
    elif contact["github"]:
        strengths.append("A GitHub/LinkedIn link is included.")

    for name, level in (("Education", "high"), ("Skills", "high"), ("Projects", "medium"), ("Experience", "medium")):
        if name not in sections:
            if name == "Experience":
                add(level, "Add an Experience or Internships section. If you have none yet, add training, freelance or open-source work.")
            else:
                add(level, f"Add a clearly labelled “{name}” section (ATS systems look for standard headings).")
    if "Summary / Objective" not in sections:
        add("low", "Add a 2-3 line professional summary tailored to the role you are targeting.")
    if len(sections) >= 4:
        strengths.append("The resume uses standard section headings, which helps ATS parsing.")

    wc = stats["word_count"]
    if wc < 250:
        add("high", f"The resume is short ({wc} words). Expand projects and experience with what you built and the outcome.")
    elif wc > 900:
        add("medium", f"The resume is long ({wc} words). Aim for one page for students/freshers (two at most) by trimming older or weak points.")
    else:
        strengths.append(f"Length is appropriate ({wc} words).")

    if stats["bullet_count"] < 4:
        add("medium", "Use bullet points for projects and experience; dense paragraphs are hard to scan.")
    if stats["action_verb_lines"] < 3:
        add("medium", "Start bullets with strong action verbs (built, designed, implemented, optimised) instead of passive phrases.")
    else:
        strengths.append("Several bullets start with strong action verbs.")
    if stats["quantified_lines"] < 2:
        add("high", "Quantify your impact where it is true (for example, “reduced load time by 30%” or “used by 200 students”).")
    else:
        strengths.append("Some achievements are quantified with numbers.")

    weak = [p for p in ("responsible for", "worked on", "helped with", "duties included", "hard working", "hardworking",
                        "team player", "good communication skills", "fast learner") if p in text.lower()]
    if weak:
        add("low", "Replace vague phrases (" + ", ".join(f"“{w}”" for w in weak[:4]) + ") with specific actions and results.")
    if stats["first_person_count"] > 1:
        add("low", "Avoid first-person wording such as “I am” or “I worked”; write concise bullet statements instead.")

    if len(skills) < 6:
        add("high", f"Only {len(skills)} recognisable skills were found. List your technical skills explicitly in a Skills section.")
    elif len(skills) >= 10:
        strengths.append(f"{len(skills)} relevant skills/keywords were detected.")

    return strengths, improvements


def detect_target_role(role_text):
    """Map a free-text role to a known role profile name (or None)."""
    if not role_text:
        return None
    role_text = role_text.lower()
    best, best_len = None, 0
    for name, profile in ROLES.items():
        if name.lower() in role_text:
            return name
        for kw in profile["keywords"]:
            if re.search(r"(?<![a-z])" + re.escape(kw) + r"(?![a-z])", role_text) and len(kw) > best_len:
                best, best_len = name, len(kw)
    return best


def missing_skills_for_role(role_name, skills):
    profile = ROLES[role_name]
    return {
        "core": [s for s in profile["core"] if s not in skills],
        "nice": [s for s in profile["nice"] if s not in skills],
    }


def learning_step(skill):
    category = SKILLS[skill][0] if skill in SKILLS else None
    return {"skill": skill, "category": category, "suggestion": LEARNING_HINTS.get(category, "Learn it through a small hands-on project.")}


def analyze_resume(text, target_role=""):
    sections = detect_sections(text)
    skills = find_skills(text)
    stats = _stats(text)
    contact = {
        "email": bool(EMAIL_RE.search(text)),
        "phone": bool(PHONE_RE.search(text)),
        "linkedin": bool(LINKEDIN_RE.search(text)),
        "github": bool(GITHUB_RE.search(text)),
    }
    overall, ats, breakdown = score_resume(text, sections, skills, stats, contact)
    strengths, improvements = build_feedback(text, sections, skills, stats, contact)

    role_name = detect_target_role(target_role)
    role_gap = None
    if role_name:
        gap = missing_skills_for_role(role_name, skills)
        role_gap = {
            "role": role_name,
            "missing_core_skills": gap["core"],
            "missing_nice_skills": gap["nice"],
            "learning_plan": [learning_step(s) for s in gap["core"][:5]],
        }
        if gap["core"]:
            improvements.append({
                "priority": "high",
                "text": f"For {role_name} roles, recruiters expect: {', '.join(gap['core'][:6])}. "
                        "Add the ones you genuinely know to your Skills section and projects.",
            })

    # Highest priority first (stable sort keeps the original order within a priority).
    order = {"high": 0, "medium": 1, "low": 2}
    improvements.sort(key=lambda i: order[i["priority"]])

    by_category = {}
    for skill, category in sorted(skills.items()):
        by_category.setdefault(category, []).append(skill)

    return {
        "scores": {"overall": overall, "ats": ats, "breakdown": breakdown, "weights": WEIGHTS},
        "contact": contact,
        "sections_found": sections,
        "sections_missing": [s for s in ("Education", "Skills", "Projects", "Experience") if s not in sections],
        "skills_by_category": by_category,
        "skills": sorted(skills),
        "stats": stats,
        "strengths": strengths,
        "improvements": improvements,
        "target_role": role_name or (target_role.strip() or None),
        "role_gap": role_gap,
    }
