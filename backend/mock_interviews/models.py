import uuid
from django.db import models


class InterviewSession(models.Model):
    INTERVIEW_TYPES = [
        ("HR", "HR Interview"),
        ("TECHNICAL", "Technical Interview"),
        ("BEHAVIORAL", "Behavioral Interview"),
        ("PROJECT", "Project-Based Interview"),
    ]

    DIFFICULTIES = [
        ("EASY", "Easy"),
        ("MEDIUM", "Medium"),
        ("HARD", "Hard"),
    ]

    STATUSES = [
        ("IN_PROGRESS", "In Progress"),
        ("COMPLETED", "Completed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.CharField(max_length=255, blank=True, default="")
    job_role = models.CharField(max_length=150)
    interview_type = models.CharField(max_length=20, choices=INTERVIEW_TYPES)
    difficulty = models.CharField(max_length=10, choices=DIFFICULTIES, default="MEDIUM")
    status = models.CharField(max_length=20, choices=STATUSES, default="IN_PROGRESS")
    total_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.job_role} - {self.interview_type}"


class InterviewQuestion(models.Model):
    session = models.ForeignKey(
        InterviewSession,
        on_delete=models.CASCADE,
        related_name="questions",
    )
    question_text = models.TextField()
    order = models.PositiveIntegerField(default=1)
    max_score = models.PositiveIntegerField(default=10)

    def __str__(self):
        return self.question_text[:80]


class InterviewAnswer(models.Model):
    question = models.ForeignKey(
        InterviewQuestion,
        on_delete=models.CASCADE,
        related_name="answers",
    )
    answer_text = models.TextField(blank=True, default="")
    score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    feedback = models.TextField(blank=True, default="")
    strengths = models.JSONField(default=list, blank=True)
    improvements = models.JSONField(default=list, blank=True)
    submitted_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Answer for question {self.question_id}"