"""Career recommendations from the skills found in a resume."""

from .analyzer import learning_step
from .skills_data import ROLES

CORE_WEIGHT = 2
NICE_WEIGHT = 1


def recommend_careers(skills, top_n=4):
    skill_set = set(skills)
    results = []
    for role, profile in ROLES.items():
        core, nice = profile["core"], profile["nice"]
        total = CORE_WEIGHT * len(core) + NICE_WEIGHT * len(nice)
        got = CORE_WEIGHT * sum(s in skill_set for s in core) + NICE_WEIGHT * sum(s in skill_set for s in nice)
        missing_core = [s for s in core if s not in skill_set]
        results.append({
            "role": role,
            "fit_percent": round(100 * got / total, 1),
            "matched_skills": [s for s in core + nice if s in skill_set],
            "missing_core_skills": missing_core,
            "next_steps": [learning_step(s) for s in missing_core[:3]],
        })
    results.sort(key=lambda r: (-r["fit_percent"], len(r["missing_core_skills"])))
    return results[:top_n]
