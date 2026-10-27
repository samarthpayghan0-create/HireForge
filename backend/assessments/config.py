
"""Configuration for HireForge Member 2 assessments."""

ALLOWED_QUESTION_COUNTS = (25, 50)

DIFFICULTY_LEVELS = ("medium", "hard")

DEFAULT_QUESTION_COUNT = 25
DEFAULT_DIFFICULTY = "medium"

ASSESSMENT_TYPES = (
    "aptitude",
    "dsa",
    "technical",
)


def validate_assessment_config(question_count, difficulty):
    """Validate the requested assessment configuration."""

    if question_count not in ALLOWED_QUESTION_COUNTS:
        raise ValueError(
            "Question count must be either 25 or 50."
        )

    if difficulty not in DIFFICULTY_LEVELS:
        raise ValueError(
            "Difficulty must be medium or hard."
        )

    return {
        "question_count": question_count,
        "difficulty": difficulty,
    }

