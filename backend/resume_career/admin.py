from django.contrib import admin

from .models import Resume, ResumeAnalysis


@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ("original_filename", "user", "file_type", "word_count", "created_at")
    list_filter = ("file_type",)
    search_fields = ("original_filename", "user__username", "user__email")
    exclude = ("extracted_text",)  # keep personal resume text out of the admin list/forms


@admin.register(ResumeAnalysis)
class ResumeAnalysisAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "kind", "target_role", "overall_score", "ai_used", "created_at")
    list_filter = ("kind", "ai_used")
    search_fields = ("user__username", "user__email", "target_role")
    exclude = ("result", "job_description")
