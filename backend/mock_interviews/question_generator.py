import json
import logging
import random

from .gemini_client import GeminiNotConfigured, generate_json

logger = logging.getLogger(__name__)


DIFFICULTY_GUIDANCE = {
    "EASY": "Ask beginner-friendly questions about fundamentals and simple examples.",
    "MEDIUM": "Ask practical questions involving implementation, debugging, testing, and trade-offs.",
    "HARD": "Ask challenging questions involving architecture, optimization, security, edge cases, and design decisions.",
}

ROLE_QUESTIONS = {
    "HR": {
        "EASY": [
            "Tell me about yourself and your career goals.",
            "Why are you interested in this job role?",
            "What are your main strengths?",
            "What skills are you currently improving?",
        ],
        "MEDIUM": [
            "Describe a difficult task you completed and how you approached it.",
            "How do you prioritize tasks when multiple deadlines compete?",
            "Tell me about a time you received constructive criticism.",
            "Why should an employer choose you for this role?",
        ],
        "HARD": [
            "Describe a professional setback and what you changed afterward.",
            "How would you handle a disagreement with your manager?",
            "Tell me about a time you took initiative without being asked.",
            "How would you respond if a deadline conflicted with quality requirements?",
        ],
    },
    "BEHAVIORAL": {
        "EASY": [
            "Describe a time you learned a new skill.",
            "Tell me about a time you helped a teammate.",
            "How do you organize your daily tasks?",
            "Describe a goal you achieved through consistent effort.",
        ],
        "MEDIUM": [
            "Describe a disagreement in a team and how you resolved it.",
            "Tell me about a mistake you made and how you corrected it.",
            "Describe a time you worked under pressure.",
            "Tell me about a time you adapted to changing requirements.",
        ],
        "HARD": [
            "Describe a time you influenced a decision without formal authority.",
            "How did you make an important decision with incomplete information?",
            "Tell me about a time you balanced conflicting priorities.",
            "Describe a situation where you challenged an established process.",
        ],
    },
    "PROJECT": {
        "EASY": [
            "What problem does your project solve?",
            "Which technologies did you use, and why?",
            "What was your individual contribution?",
            "What did you learn while building the project?",
        ],
        "MEDIUM": [
            "Explain your project's architecture and data flow.",
            "How did you design and validate the project's database?",
            "What was the most difficult bug you fixed?",
            "How did you test your project's main features?",
        ],
        "HARD": [
            "How would you scale your project for many concurrent users?",
            "What security risks exist in your project, and how would you mitigate them?",
            "What architectural decisions would you change if you rebuilt the project?",
            "How would you improve reliability, monitoring, and error handling?",
        ],
    },
}

VALID_TYPES = {"HR", "TECHNICAL", "BEHAVIORAL", "PROJECT"}
VALID_DIFFICULTIES = {"EASY", "MEDIUM", "HARD"}


def _clean(value):
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)):
        return str(value)
    return ""


def _extract_items(value, preferred_keys):
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []

    if not isinstance(value, list):
        return []

    results = []

    for item in value:
        if isinstance(item, str):
            text = item.strip()
        elif isinstance(item, dict):
            text = ""

            for key in preferred_keys:
                candidate = _clean(item.get(key))
                if candidate:
                    text = candidate
                    break

            if not text:
                text = next(
                    (
                        _clean(v)
                        for k, v in item.items()
                        if k.lower() not in {
                            "rating", "level", "score",
                            "proficiency", "id",
                        }
                        and isinstance(v, (str, int, float))
                        and _clean(v)
                    ),
                    "",
                )
        else:
            text = ""

        if text and text not in results:
            results.append(text)

    return results


def _profile_context(profile):
    skills = _extract_items(
        profile.get("technical_skills", []),
        ["name", "skill", "skill_name", "title", "technology"],
    )
    projects = _extract_items(
        profile.get("projects", []),
        ["name", "project_name", "title", "description"],
    )
    internships = _extract_items(
        profile.get("internships", []),
        ["company", "company_name", "role", "title", "description"],
    )
    certifications = _extract_items(
        profile.get("certifications", []),
        ["name", "title", "certification_name"],
    )
    return skills, projects, internships, certifications


def _unique_questions(questions):
    result = []
    seen = set()

    for question in questions:
        if not isinstance(question, str):
            continue

        question = " ".join(question.split()).strip()
        normalized = question.casefold()

        if question and normalized not in seen:
            seen.add(normalized)
            result.append(question)

    return result


def _generate_fallback_questions(profile, interview_type, difficulty, count):
    role = str(profile.get("target_role") or "the selected job role").strip()
    skills, projects, internships, certifications = _profile_context(profile)
    questions = []

    if interview_type == "TECHNICAL":
        templates = {
            "EASY": [
                "Explain the basic concepts of {skill} and give a simple example.",
                "What are the main features of {skill}, and when would you use them?",
                "Explain a common beginner mistake in {skill} and how to avoid it.",
            ],
            "MEDIUM": [
                "Describe a practical problem you could solve using {skill}. Walk through your approach.",
                "How would you test and debug a feature implemented using {skill}?",
                "Compare two approaches to solving a problem with {skill}. Explain their trade-offs.",
            ],
            "HARD": [
                "How would you optimize a complex {skill} implementation for performance and maintainability?",
                "How would you design a reliable, secure solution using {skill} for production?",
                "Explain edge cases that could break a solution using {skill} and how you would handle them.",
            ],
        }

        for skill in skills:
            questions.extend(
                template.format(skill=skill, role=role)
                for template in templates[difficulty]
            )

        for project in projects:
            questions.append(
                f"Explain the technical decisions you made in '{project}' "
                f"and how they relate to a {role} role."
            )

        for certification in certifications:
            questions.append(
                f"What practical knowledge from '{certification}' "
                f"could you apply as a {role}?"
            )

        for internship in internships:
            questions.append(
                f"What technical responsibilities did you have during "
                f"'{internship}', and how did they prepare you for a {role} position?"
            )

        if not skills:
            questions.extend([
                f"What technical concepts are essential for a {role}?",
                "How would you debug an application when the cause of a failure is unclear?",
                "How would you test a feature before releasing it?",
            ])

    elif interview_type in ROLE_QUESTIONS:
        questions.extend(ROLE_QUESTIONS[interview_type][difficulty])

        if interview_type == "HR":
            questions.append(
                f"Why are your current skills and experiences a good fit for {role}?"
            )

        if interview_type == "PROJECT":
            for project in projects:
                questions.extend([
                    f"What problem does '{project}' solve, and who benefits from it?",
                    f"Explain your individual contribution to '{project}'.",
                ])

        if interview_type == "BEHAVIORAL" and projects:
            questions.append(
                f"Describe a challenge you faced while working on "
                f"'{projects[0]}' and how you handled it."
            )

    questions = _unique_questions(questions)
    random.shuffle(questions)

    extra_templates = [
        f"How would you approach an unfamiliar task as a {role}?",
        f"How would you validate that your solution meets the requirements for a {role}?",
        "How would you explain a difficult technical concept to a teammate?",
        "What information would you gather before choosing an implementation approach?",
        "How would you identify risks before delivering a solution?",
        "How would you determine whether your solution was successful?",
        "How would you respond if your first approach failed?",
        "What would you improve after receiving feedback on your work?",
        "How would you communicate a technical blocker to your team?",
        "How would you balance maintainability and delivery time?",
    ]

    for question in extra_templates:
        if len(questions) >= count:
            break
        if question.casefold() not in {q.casefold() for q in questions}:
            questions.append(question)

    return [
        {"question_text": question, "order": index, "max_score": 10}
        for index, question in enumerate(questions[:count], start=1)
    ]


def _generate_gemini_questions(profile, interview_type, difficulty, count):
    skills, projects, internships, certifications = _profile_context(profile)

    profile_context = {
        "target_role": profile.get("target_role", ""),
        "technical_skills": skills,
        "projects": projects,
        "internships": internships,
        "certifications": certifications,
        "education": profile.get("degree", ""),
        "graduation_year": profile.get("graduation_year", ""),
        "cgpa": profile.get("cgpa", ""),
    }

    prompt = f"""
You are an experienced technical interviewer creating a realistic mock interview.

Generate exactly {count} distinct interview questions.
Interview type: {interview_type}
Difficulty: {difficulty}
Difficulty guidance: {DIFFICULTY_GUIDANCE[difficulty]}
Target role: {profile_context["target_role"] or "Use the supplied job role context"}
Candidate profile: {json.dumps(profile_context, ensure_ascii=False)}

Requirements:
- Personalize questions to the candidate's actual skills, projects, and experience.
- For TECHNICAL interviews, focus on role-relevant technical knowledge and practical problem solving.
- For HR interviews, focus on motivation, communication, strengths, and career goals.
- For BEHAVIORAL interviews, ask situation-based questions about actions, decisions, and outcomes.
- For PROJECT interviews, focus on the candidate's actual projects and technical decisions.
- Do not invent projects, employment, certifications, or experience the profile does not contain.
- Avoid repeated or nearly identical questions.
- Match the requested difficulty.
- Ask questions only; do not include answers, explanations, markdown, or numbering in the question text.
- Return valid JSON in this exact shape:
{{"questions": ["question one", "question two"]}}
"""

    data = generate_json(prompt, max_output_tokens=8192)
    raw_questions = data.get("questions") if isinstance(data, dict) else None

    if not isinstance(raw_questions, list):
        raise ValueError("Gemini returned an unexpected response format.")

    questions = _unique_questions(
        [question for question in raw_questions if isinstance(question, str)]
    )

    if len(questions) < count:
        raise ValueError("Gemini returned too few distinct questions.")

    return [
        {"question_text": question, "order": index, "max_score": 10}
        for index, question in enumerate(questions[:count], start=1)
    ]


def generate_questions(profile, interview_type, difficulty, count=10, job_role=None):
    interview_type = str(interview_type).upper()
    difficulty = str(difficulty).upper()

    # The role chosen for this interview overrides the profile's target role.
    profile = dict(profile or {})
    if job_role and str(job_role).strip():
        profile["target_role"] = str(job_role).strip()

    if interview_type not in VALID_TYPES:
        raise ValueError("Unsupported interview type.")

    if difficulty not in VALID_DIFFICULTIES:
        raise ValueError("Unsupported difficulty.")

    if not isinstance(count, int) or isinstance(count, bool) or count < 1 or count > 30:
        raise ValueError("Question count must be between 1 and 30.")

    try:
        return _generate_gemini_questions(
            profile, interview_type, difficulty, count
        )
    except GeminiNotConfigured:
        logger.warning("Gemini API key not configured; using fallback questions.")
        return _generate_fallback_questions(
            profile, interview_type, difficulty, count
        )
    except Exception:
        logger.exception("Gemini question generation failed; using fallback.")
        return _generate_fallback_questions(
            profile, interview_type, difficulty, count
        )
