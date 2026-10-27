
from django.contrib import admin
from .models import InterviewSession, InterviewQuestion, InterviewAnswer


class InterviewQuestionInline(admin.TabularInline):
    model = InterviewQuestion
    extra = 1


class InterviewAnswerInline(admin.TabularInline):
    model = InterviewAnswer
    extra = 0


@admin.register(InterviewSession)
class InterviewSessionAdmin(admin.ModelAdmin):
    list_display = (
        "job_role",
        "interview_type",
        "difficulty",
        "status",
        "total_score",
        "created_at",
    )
    list_filter = ("interview_type", "difficulty", "status")
    search_fields = ("job_role", "user_id")
    inlines = [InterviewQuestionInline]


@admin.register(InterviewQuestion)
class InterviewQuestionAdmin(admin.ModelAdmin):
    list_display = ("session", "order", "max_score")
    search_fields = ("question_text",)


@admin.register(InterviewAnswer)
class InterviewAnswerAdmin(admin.ModelAdmin):
    list_display = ("question", "score", "submitted_at")
    inlines = []
