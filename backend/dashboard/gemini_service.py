
import json
import os
import re

import requests


GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent"
)
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

class GeminiAssessmentError(Exception):
    pass


def _parse_json_response(text):
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise GeminiAssessmentError(
            "Gemini returned an unreadable assessment."
        ) from exc

    if not isinstance(result, dict):
        raise GeminiAssessmentError(
            "Gemini returned an unexpected assessment format."
        )

    return result


def generate_readiness_assessment(profile):
    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        raise GeminiAssessmentError(
            "Gemini API key is missing from the backend environment."
        )

    profile_data = {
        "target_role": profile.target_role,
        "degree": profile.degree,
        "graduation_year": profile.graduation_year,
        "cgpa_out_of_10": (
            float(profile.cgpa) if profile.cgpa is not None else None
        ),
        "dsa_rating_out_of_10": profile.dsa_rating,
        "aptitude_rating_out_of_10": profile.aptitude_rating,
        "communication_rating_out_of_10": profile.communication_rating,
        "technical_skills": profile.technical_skills or [],
        "projects": profile.projects or [],
        "internships": profile.internships or [],
        "certifications": profile.certifications or [],
    }

    instructions = """
You are HireForge's career-readiness coach.
Assess the student's preparation for their target role using only the
provided profile. Be practical, supportive, specific, and honest.
Do not invent achievements or skills. Treat missing information as unknown.

Return only a valid JSON object with exactly these keys:
{
  "target_role": "string",
  "readiness_score": 0,
  "summary": "string",
  "strengths": ["string"],
  "skill_gaps": [
    {"skill": "string", "reason": "string", "priority": "High"}
  ],
  "action_plan": [
    {"step": "string", "reason": "string"}
  ],
  "profile_items_to_improve": ["string"],
  "limitations": "string"
}

Rules:
- readiness_score must be an integer from 0 to 100.
- It is an indicative preparation score, not a hiring probability.
- Include up to 4 strengths, 5 skill gaps, 5 next steps, and 4 profile improvements.
- Priority must be High, Medium, or Low.
- Keep explanations concise and actionable.
"""

    payload = {
        "system_instruction": {
            "parts": [{"text": instructions}]
        },
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": "Student profile JSON:\n"
                        + json.dumps(profile_data, ensure_ascii=False)
                    }
                ],
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.2,
        },
    }

    try:
        response = requests.post(
            GEMINI_API_URL.format(model=GEMINI_MODEL),
            headers={
                "x-goog-api-key": api_key,
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=(10, 90),
        )
    except requests.Timeout as exc:
        raise GeminiAssessmentError(
            "Gemini timed out. Please try again."
        ) from exc
    except requests.RequestException as exc:
        raise GeminiAssessmentError(
            "Could not connect to Gemini. Check the backend connection."
        ) from exc

    if not response.ok:
        try:
            details = response.json().get("error", {}).get("message", "")
        except ValueError:
            details = ""

        raise GeminiAssessmentError(
            f"Gemini HTTP {response.status_code}: "
            f"{details or 'Request rejected.'}"
        )

    try:
        response_data = response.json()
        output_text = response_data["candidates"][0]["content"]["parts"][0]["text"]
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise GeminiAssessmentError(
            "Gemini returned an unexpected response format."
        ) from exc

    result = _parse_json_response(output_text)

    score = result.get("readiness_score")
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        raise GeminiAssessmentError("Gemini returned an invalid readiness score.")

    result["readiness_score"] = max(0, min(100, round(score)))
    result["target_role"] = str(result.get("target_role") or profile.target_role)
    result["summary"] = str(result.get("summary") or "")
    result["limitations"] = str(result.get("limitations") or "")

    for key in ("strengths", "skill_gaps", "action_plan", "profile_items_to_improve"):
        if not isinstance(result.get(key), list):
            result[key] = []

    valid_skill_gaps = []
    for item in result["skill_gaps"]:
        if not isinstance(item, dict):
            continue

        skill = str(item.get("skill") or "").strip()
        if not skill:
            continue

        priority = str(item.get("priority") or "Medium").title()
        if priority not in {"High", "Medium", "Low"}:
            priority = "Medium"

        valid_skill_gaps.append({
            "skill": skill,
            "reason": str(item.get("reason") or "").strip(),
            "priority": priority,
        })

    result["skill_gaps"] = valid_skill_gaps
    return result
