
"""Question selection and scoring service for HireForge Member 2."""

import random

from assessments.config import (
    ALLOWED_QUESTION_COUNTS,
    ASSESSMENT_TYPES,
    DIFFICULTY_LEVELS,
)
from assessments.questions import QUESTIONS


def get_assessment_type(question):
    """Determine the assessment type from a question ID."""
    question_id = question.get("id", "")

    if question_id.startswith("apt_"):
        return "aptitude"
    if question_id.startswith("dsa_"):
        return "dsa"
    if question_id.startswith("tech_"):
        return "technical"

    return None


def validate_request(assessment_type, difficulty, question_count):
    """Validate assessment type, difficulty, and requested count."""

    if assessment_type not in ASSESSMENT_TYPES:
        raise ValueError(
            "Assessment type must be aptitude, dsa, or technical."
        )

    if difficulty not in DIFFICULTY_LEVELS:
        raise ValueError("Difficulty must be medium or hard.")

    if question_count not in ALLOWED_QUESTION_COUNTS:
        raise ValueError("Question count must be either 25 or 50.")


def get_questions(assessment_type, difficulty, question_count=25):
    """Select questions without exposing answer keys or explanations."""

    validate_request(assessment_type, difficulty, question_count)

    eligible = [
        question
        for question in QUESTIONS
        if get_assessment_type(question) == assessment_type
        and question.get("difficulty") == difficulty
    ]

    if len(eligible) < question_count:
        raise ValueError(
            f"Not enough questions available. "
            f"Requested {question_count}, found {len(eligible)}."
        )

    selected = random.sample(eligible, question_count)

    # Never send correct answers or explanations to the frontend.
    return [
        {
            "id": question["id"],
            "topic": question.get("topic", ""),
            "question": question["question"],
            "options": question["options"],
        }
        for question in selected
    ]


def score_answers(question_ids, submitted_answers):
    """Score submitted answers against the server-side question bank.

    question_ids: IDs selected for the assessment attempt.
    submitted_answers: mapping of question ID to answer letter,
                       such as {"dsa_med_001": "A"}.
    """

    if not isinstance(submitted_answers, dict):
        raise ValueError("Answers must be supplied as a dictionary.")

    question_map = {
        question["id"]: question
        for question in QUESTIONS
        if question.get("id") in question_ids
    }

    if len(question_map) != len(question_ids):
        raise ValueError("One or more assessment question IDs are invalid.")

    correct_count = 0
    results = []

    for question_id in question_ids:
        question = question_map[question_id]
        submitted = submitted_answers.get(question_id)
        correct = question.get("correct_answer")

        # Accept only valid answer letters.
        valid_letters = [
            chr(ord("A") + index)
            for index in range(len(question.get("options", [])))
        ]

        if not isinstance(submitted, str):
            submitted = ""
        submitted = submitted.strip().upper()

        is_correct = submitted == correct and submitted in valid_letters

        if is_correct:
            correct_count += 1

        results.append({
            "question_id": question_id,
            "submitted_answer": submitted or None,
            "is_correct": is_correct,
            "correct_answer": correct,
            "explanation": question.get("explanation", ""),
        })

    total = len(question_ids)

    return {
        "total_questions": total,
        "correct_answers": correct_count,
        "incorrect_or_unanswered": total - correct_count,
        "score_percentage": round(
            (correct_count / total) * 100, 2
        ) if total else 0,
        "results": results,
    }
