from django.urls import path

from . import views

# Mounted at /api/resume/ in the project urls.
urlpatterns = [
    path("upload/", views.ResumeUploadView.as_view(), name="resume-upload"),
    path("resumes/", views.ResumeListView.as_view(), name="resume-list"),
    path("resumes/<int:pk>/", views.ResumeDetailView.as_view(), name="resume-detail"),
    path("analyze/", views.AnalyzeView.as_view(), name="resume-analyze"),
    path("job-match/", views.JobMatchView.as_view(), name="resume-job-match"),
    path("history/", views.HistoryListView.as_view(), name="resume-history"),
    path("history/<int:pk>/", views.HistoryDetailView.as_view(), name="resume-history-detail"),
]
