
from django.urls import path

from . import views

urlpatterns = [
    path("start/", views.start_assessment, name="start-assessment"),
    path(
        "submit/<uuid:attempt_id>/",
        views.submit_assessment,
        name="submit-assessment",
    ),
    path("history/", views.assessment_history, name="assessment-history"),
    path(
    "performance/",
    views.performance_summary,
    name="performance-summary",
),
]
