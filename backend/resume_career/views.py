import logging
from decimal import Decimal

from django.apps import apps
from django.db import transaction
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import ai
from .analyzer import analyze_resume
from .careers import recommend_careers
from .extraction import MAX_FILE_BYTES, ResumeFileError, extract_resume_text
from .job_match import match_job
from .models import Resume, ResumeAnalysis
from .serializers import (
    AnalyzeRequestSerializer,
    JobMatchRequestSerializer,
    ResumeAnalysisDetailSerializer,
    ResumeAnalysisSummarySerializer,
    ResumeSerializer,
)

logger = logging.getLogger(__name__)

MAX_RESUMES_PER_USER = 20


def error(message, http_status):
    return Response({"detail": message}, status=http_status)


def validation_error(serializer):
    return Response(
        {"detail": "Invalid request data.", "errors": serializer.errors},
        status=status.HTTP_400_BAD_REQUEST,
    )


def own_resume_or_404(user, resume_id):
    """Users can only ever see their own resumes (others look like 404)."""
    return Resume.objects.filter(pk=resume_id, user=user).first()


def profile_target_role(user):
    """Target role from Member 1's profile when the `dashboard` app is installed."""
    if not apps.is_installed("dashboard"):
        return ""
    try:
        from dashboard.models import StudentProfile

        profile = StudentProfile.objects.filter(user=user).first()
        return (getattr(profile, "target_role", "") or "") if profile else ""
    except Exception:  # never let an optional integration break the API
        logger.exception("Could not read target role from the student profile.")
        return ""


class ResumeUploadView(APIView):
    """POST /api/resume/upload/  (multipart field `file`)"""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        upload = request.FILES.get("file")
        if upload is None:
            return error("No file uploaded. Send the resume in the `file` field.", status.HTTP_400_BAD_REQUEST)

        if Resume.objects.filter(user=request.user).count() >= MAX_RESUMES_PER_USER:
            return error(
                f"You can store up to {MAX_RESUMES_PER_USER} resumes. Delete an old one first.",
                status.HTTP_400_BAD_REQUEST,
            )

        # Read at most one byte over the limit so an oversized file is rejected cheaply.
        data = upload.read(MAX_FILE_BYTES + 1)

        try:
            file_type, text = extract_resume_text(upload.name, data)
        except ResumeFileError as exc:
            return error(str(exc), status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception("Unexpected resume extraction failure")
            return error("The resume could not be processed.", status.HTTP_422_UNPROCESSABLE_ENTITY)

        resume = Resume.objects.create(
            user=request.user,
            original_filename=upload.name[:255],
            file_type=file_type,
            file_size=len(data),
            extracted_text=text,
            word_count=len(text.split()),
        )
        return Response(
            {"resume": ResumeSerializer(resume).data, "text_preview": text[:500]},
            status=status.HTTP_201_CREATED,
        )


class ResumeListView(APIView):
    """GET /api/resume/resumes/"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        resumes = Resume.objects.filter(user=request.user)
        return Response(ResumeSerializer(resumes, many=True).data)


class ResumeDetailView(APIView):
    """DELETE /api/resume/resumes/<id>/  (also deletes its analyses)"""

    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        resume = own_resume_or_404(request.user, pk)
        if resume is None:
            return error("Resume not found.", status.HTTP_404_NOT_FOUND)
        resume.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AnalyzeView(APIView):
    """POST /api/resume/analyze/"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AnalyzeRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error(serializer)
        data = serializer.validated_data

        resume = own_resume_or_404(request.user, data["resume_id"])
        if resume is None:
            return error("Resume not found.", status.HTTP_404_NOT_FOUND)

        target_role = data["target_role"].strip() or profile_target_role(request.user)

        result = analyze_resume(resume.extracted_text, target_role)
        result["career_recommendations"] = recommend_careers(result["skills"])

        ai_feedback = ai.ai_review(resume.extracted_text, target_role) if data["use_ai"] else None
        result["ai_feedback"] = ai_feedback

        analysis = ResumeAnalysis.objects.create(
            user=request.user,
            resume=resume,
            kind=ResumeAnalysis.KIND_GENERAL,
            target_role=(result["target_role"] or "")[:150],
            overall_score=Decimal(str(result["scores"]["overall"])),
            ats_score=Decimal(str(result["scores"]["ats"])),
            result=result,
            ai_used=ai_feedback is not None,
        )
        return Response(ResumeAnalysisDetailSerializer(analysis).data, status=status.HTTP_201_CREATED)


class JobMatchView(APIView):
    """POST /api/resume/job-match/"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = JobMatchRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error(serializer)
        data = serializer.validated_data

        resume = own_resume_or_404(request.user, data["resume_id"])
        if resume is None:
            return error("Resume not found.", status.HTTP_404_NOT_FOUND)

        result = match_job(resume.extracted_text, data["job_description"], data["job_title"])
        ai_feedback = (
            ai.ai_review(resume.extracted_text, data["job_title"], data["job_description"])
            if data["use_ai"] else None
        )
        result["ai_feedback"] = ai_feedback

        analysis = ResumeAnalysis.objects.create(
            user=request.user,
            resume=resume,
            kind=ResumeAnalysis.KIND_JOB_MATCH,
            target_role=data["job_title"].strip()[:150],
            job_description=data["job_description"],
            overall_score=Decimal(str(result["match_score"])),
            result=result,
            ai_used=ai_feedback is not None,
        )
        return Response(ResumeAnalysisDetailSerializer(analysis).data, status=status.HTTP_201_CREATED)


class HistoryListView(APIView):
    """GET /api/resume/history/?kind=general|job_match"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = ResumeAnalysis.objects.filter(user=request.user).select_related("resume")
        kind = request.query_params.get("kind")
        if kind in (ResumeAnalysis.KIND_GENERAL, ResumeAnalysis.KIND_JOB_MATCH):
            queryset = queryset.filter(kind=kind)
        return Response(ResumeAnalysisSummarySerializer(queryset[:100], many=True).data)


class HistoryDetailView(APIView):
    """GET/DELETE /api/resume/history/<id>/"""

    permission_classes = [IsAuthenticated]

    def _get(self, request, pk):
        return ResumeAnalysis.objects.filter(pk=pk, user=request.user).select_related("resume").first()

    def get(self, request, pk):
        analysis = self._get(request, pk)
        if analysis is None:
            return error("Analysis not found.", status.HTTP_404_NOT_FOUND)
        return Response(ResumeAnalysisDetailSerializer(analysis).data)

    def delete(self, request, pk):
        analysis = self._get(request, pk)
        if analysis is None:
            return error("Analysis not found.", status.HTTP_404_NOT_FOUND)
        analysis.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
