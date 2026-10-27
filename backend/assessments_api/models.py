
import uuid

from django.conf import settings
from django.db import models


class AssessmentAttempt(models.Model):
    class AssessmentType(models.TextChoices):
        APTITUDE = "aptitude", "Aptitude"
        DSA = "dsa", "Data Structures and Algorithms"
        TECHNICAL = "technical", "Technical Skills"

    class Difficulty(models.TextChoices):
        MEDIUM = "medium", "Medium"
        HARD = "hard", "Hard"

    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assessment_attempts",
    )

    assessment_type = models.CharField(
        max_length=20,
        choices=AssessmentType.choices,
    )
    difficulty = models.CharField(
        max_length=10,
        choices=Difficulty.choices,
    )
    question_count = models.PositiveSmallIntegerField(
        choices=[(25, "25 questions"), (50, "50 questions")],
    )

    # Stores the exact question IDs selected by the backend.
    question_ids = models.JSONField(default=list)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.IN_PROGRESS,
    )

    correct_answers = models.PositiveSmallIntegerField(default=0)
    score_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )

    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return (
            f"{self.user} - {self.assessment_type} "
            f"({self.difficulty}) - {self.status}"
        )


class AssessmentAnswer(models.Model):
    attempt = models.ForeignKey(
        AssessmentAttempt,
        on_delete=models.CASCADE,
        related_name="answers",
    )

    question_id = models.CharField(max_length=100)
    selected_answer = models.CharField(max_length=1, blank=True, default="")
    is_correct = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["attempt", "question_id"],
                name="unique_question_per_assessment_attempt",
            ),
        ]

    def __str__(self):
        return f"{self.attempt_id} - {self.question_id}"
