from django.conf import settings
from django.contrib import admin
from django.db import connection
from django.http import JsonResponse
from django.urls import include, path, re_path
from django.views.decorators.cache import never_cache
from django.views.static import serve as serve_static

from mock_interviews.views import InterviewPageView


@never_cache
def health(request):
    """GET /api/health/  – used by the post-deploy smoke test and uptime monitors."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        database = "ok"
    except Exception:  # never leak connection details
        database = "error"
    code = 200 if database == "ok" else 503
    return JsonResponse({"status": "ok" if code == 200 else "degraded", "database": database}, status=code)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health, name="health"),
    path("api/assessments/", include("assessments_api.urls")),   # Member 2
    path("api/interviews/", include("mock_interviews.urls")),    # Member 3
    path("api/resume/", include("resume_career.urls")),          # Member 4
    path("api/", include("dashboard.urls")),                     # Member 1 (keep last)
    path("interview/", InterviewPageView.as_view(), name="interview-page"),
]



def frontend(request, path=""):
    """Serve files from /public; a folder URL (or "/") serves its index.html.

    `django.views.static.serve` blocks path traversal (".." etc.).
    """
    if not path or path.endswith("/"):
        path += "index.html"
    return serve_static(request, path, document_root=settings.PUBLIC_DIR)


if settings.SERVE_FRONTEND:
    # Local development: Django also serves the HTML/CSS/JS in /public so the whole
    # app runs on http://127.0.0.1:8000. On Vercel these files are served by the CDN.
    urlpatterns += [
        path("", frontend),
        re_path(r"^(?P<path>.+)$", frontend),
    ]
