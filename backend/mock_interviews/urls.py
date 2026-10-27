
from django.urls import path

from .views import (
    InterviewSessionListCreateView,
    InterviewSessionDetailView,
    SubmitAnswerView,
    CompleteInterviewView,
)

urlpatterns = [
    path("sessions/", InterviewSessionListCreateView.as_view(), name="session-list-create"),
    path("sessions/<uuid:id>/", InterviewSessionDetailView.as_view(), name="session-detail"),
    path("questions/<int:question_id>/answer/", SubmitAnswerView.as_view(), name="submit-answer"),
    path("sessions/<uuid:session_id>/complete/", CompleteInterviewView.as_view(), name="complete-interview"),
]
