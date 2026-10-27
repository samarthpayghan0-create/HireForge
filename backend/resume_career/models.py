from django.conf import settings
from django.db import models


class Resume(models.Model):
    """Metadata and extracted text of an uploaded resume.

    The uploaded file itself is NOT stored: only the extracted text is kept,
    which means no MEDIA configuration is needed and less personal data is held.
    """

    FILE_TYPES = [("pdf", "PDF"), ("docx", "DOCX")]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="resumes",
    )
    original_filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=10, choices=FILE_TYPES)
    file_size = models.PositiveIntegerField(help_text="Size in bytes")
    extracted_text = models.TextField()
    word_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.original_filename} ({self.user})"


class ResumeAnalysis(models.Model):
    """One saved result: either a general analysis or a job-description match."""

    KIND_GENERAL = "general"
    KIND_JOB_MATCH = "job_match"
    KINDS = [(KIND_GENERAL, "General analysis"), (KIND_JOB_MATCH, "Job match")]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="resume_analyses",
    )
    resume = models.ForeignKey(
        Resume,
        on_delete=models.CASCADE,
        related_name="analyses",
    )
    kind = models.CharField(max_length=20, choices=KINDS)
    target_role = models.CharField(max_length=150, blank=True, default="")
    job_description = models.TextField(blank=True, default="")
    overall_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    ats_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    result = models.JSONField(default=dict)
    ai_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "resume analyses"

    def __str__(self):
        return f"{self.get_kind_display()} #{self.pk} - {self.user}"
