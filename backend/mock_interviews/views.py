import logging
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from django.views.generic import TemplateView
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import InterviewSession, InterviewQuestion, InterviewAnswer
from .serializers import InterviewSessionSerializer, InterviewAnswerSerializer
from .profile_service import get_student_profile, Member1ProfileError
from .question_generator import generate_questions
from .answer_evaluator import evaluate_answer
from .gemini_client import GeminiNotConfigured

logger = logging.getLogger(__name__)

MAX_ANSWER_LENGTH = 5000


class InterviewPageView(TemplateView):
    """Serves the mock-interview web page."""

    template_name = "mock_interviews/interview.html"


class InterviewSessionListCreateView(generics.ListCreateAPIView):
    serializer_class = InterviewSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return InterviewSession.objects.filter(
            user_id=str(self.request.user.pk)
        ).prefetch_related("questions", "questions__answers")

    def create(self, request, *args, **kwargs):
        # Merged project: the student's own token works for every module.
        # Standalone: Member 1's token may be sent separately.
        member1_token = request.headers.get("X-Member1-Token") or getattr(
            request.auth, "key", None
        )

        try:
            profile = get_student_profile(token=member1_token, user=request.user)
        except Member1ProfileError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        job_role = str(
            request.data.get("job_role") or profile.get("target_role") or ""
        ).strip()
        interview_type = request.data.get("interview_type", "TECHNICAL")
        difficulty = request.data.get("difficulty", "MEDIUM")

        if not job_role:
            return Response(
                {"detail": "Set your target role in your profile or enter a job role."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(job_role) > 150:
            return Response(
                {"detail": "Job role must be 150 characters or fewer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if interview_type not in dict(InterviewSession.INTERVIEW_TYPES):
            return Response(
                {"detail": "Invalid interview_type."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if difficulty not in dict(InterviewSession.DIFFICULTIES):
            return Response(
                {"detail": "Invalid difficulty."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            generated_questions = generate_questions(
                profile=profile,
                interview_type=interview_type,
                difficulty=difficulty,
                count=10,
                job_role=job_role,
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            session = InterviewSession.objects.create(
                user_id=str(request.user.pk),
                job_role=job_role,
                interview_type=interview_type,
                difficulty=difficulty,
            )

            InterviewQuestion.objects.bulk_create([
                InterviewQuestion(
                    session=session,
                    question_text=item["question_text"],
                    order=item["order"],
                    max_score=item["max_score"],
                )
                for item in generated_questions
            ])

        session.refresh_from_db()

        return Response(
            {
                "session": InterviewSessionSerializer(session).data,
                "message": "Interview session and personalized questions created successfully.",
            },
            status=status.HTTP_201_CREATED,
        )


class InterviewSessionDetailView(generics.RetrieveDestroyAPIView):
    serializer_class = InterviewSessionSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "id"

    def get_queryset(self):
        return InterviewSession.objects.filter(
            user_id=str(self.request.user.pk)
        ).prefetch_related("questions", "questions__answers")


class SubmitAnswerView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, question_id):
        try:
            question = InterviewQuestion.objects.select_related(
                "session"
            ).get(
                id=question_id,
                session__user_id=str(request.user.pk),
                session__status="IN_PROGRESS",
            )
        except InterviewQuestion.DoesNotExist:
            return Response(
                {"detail": "Question not found or interview is not in progress."},
                status=status.HTTP_404_NOT_FOUND,
            )

        answer_text = request.data.get("answer_text", "")

        if not isinstance(answer_text, str) or not answer_text.strip():
            return Response(
                {"answer_text": "This field is required and must be text."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        answer_text = answer_text.strip()

        if len(answer_text) > MAX_ANSWER_LENGTH:
            return Response(
                {"answer_text": f"Answer must be {MAX_ANSWER_LENGTH} characters or fewer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            evaluation = evaluate_answer(
                question=question.question_text,
                answer_text=answer_text,
                job_role=question.session.job_role,
                interview_type=question.session.interview_type,
                difficulty=question.session.difficulty,
            )
        except GeminiNotConfigured:
            return Response(
                {
                    "detail": (
                        "AI evaluation is not configured on the server "
                        "(GEMINI_API_KEY is missing). Your answer was not saved."
                    )
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception:
            logger.exception("Answer evaluation failed")
            return Response(
                {
                    "detail": (
                        "AI evaluation is temporarily unavailable. "
                        "Your answer was not saved. Please try again."
                    )
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        with transaction.atomic():
            answer = InterviewAnswer.objects.create(
                question=question,
                answer_text=answer_text,
                score=evaluation["score"],
                feedback=evaluation["feedback"],
                strengths=evaluation["strengths"],
                improvements=evaluation["improvements"],
            )

        return Response(
            InterviewAnswerSerializer(answer).data,
            status=status.HTTP_201_CREATED,
        )


class CompleteInterviewView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        try:
            session = InterviewSession.objects.get(
                id=session_id,
                user_id=str(request.user.pk),
            )
        except InterviewSession.DoesNotExist:
            return Response(
                {"detail": "Interview session not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if session.status == "COMPLETED":
            return Response(
                {"detail": "This interview is already completed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        questions = InterviewQuestion.objects.filter(session=session)
        question_count = questions.count()

        if question_count == 0:
            return Response(
                {"detail": "Cannot complete an interview without questions."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        latest_answers = [
            question.answers.order_by("-submitted_at").first()
            for question in questions
        ]

        if any(answer is None for answer in latest_answers):
            return Response(
                {"detail": "Please answer every question before completing the interview."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        session.total_score = (
            sum((answer.score for answer in latest_answers), Decimal("0"))
            / question_count
        ).quantize(Decimal("0.01"))
        session.status = "COMPLETED"
        session.completed_at = timezone.now()
        session.save(
            update_fields=["total_score", "status", "completed_at"]
        )

        return Response(InterviewSessionSerializer(session).data)
