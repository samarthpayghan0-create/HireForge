
from django.conf import settings
from django.db import models


class StudentProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="student_profile",
    )
    full_name = models.CharField(max_length=150, blank=True)
    college_name = models.CharField(max_length=200, blank=True)
    degree = models.CharField(max_length=100, blank=True)
    graduation_year = models.PositiveIntegerField(null=True, blank=True)
    cgpa = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
    )
    dsa_rating = models.PositiveSmallIntegerField(null=True, blank=True)
    aptitude_rating = models.PositiveSmallIntegerField(null=True, blank=True)
    communication_rating = models.PositiveSmallIntegerField(null=True, blank=True)
    technical_skills = models.JSONField(default=list, blank=True)
    projects = models.JSONField(default=list, blank=True)
    internships = models.JSONField(default=list, blank=True)
    certifications = models.JSONField(default=list, blank=True)
    target_role = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_name or self.user.get_username()
class ReadinessAssessment(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="readiness_assessments",
    )
    assessment = models.JSONField(default=dict)
    disclaimer = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Readiness Assessment - {self.user}"