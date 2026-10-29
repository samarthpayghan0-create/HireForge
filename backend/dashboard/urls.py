from django.urls import path

from .views import (
    LoginView,
    ReadinessAssessmentView,
    RegisterView,
    StudentPerformanceView,
    StudentProfileView,
)


urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("profile/", StudentProfileView.as_view(), name="student-profile"),
    path(
        "assessment/",
        ReadinessAssessmentView.as_view(),
        name="readiness-assessment",
    ),
    path(
        "performance/",
        StudentPerformanceView.as_view(),
        name="student-performance",
    ),
]
