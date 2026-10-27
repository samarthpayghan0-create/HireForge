
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from assessments.question_service import get_questions, score_answers
from assessments.questions import QUESTIONS

from .models import AssessmentAnswer, AssessmentAttempt
from .serializers import AssessmentAttemptSerializer

from django.db.models import Avg, Max, Count, Sum



def get_question_bank():
    """Return the server-side question bank indexed by question ID."""
    return {question["id"]: question for question in QUESTIONS}


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def start_assessment(request):
    assessment_type = request.data.get("assessment_type", "aptitude")
    difficulty = request.data.get("difficulty", "medium")
    question_count = request.data.get("question_count", 25)

    try:
        if isinstance(question_count, bool):
            raise ValueError("Question count must be either 25 or 50.")

        question_count = int(question_count)

        selected_questions = get_questions(
            assessment_type,
            difficulty,
            question_count,
        )
    except (ValueError, TypeError) as exc:
        return Response(
            {"error": str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    attempt = AssessmentAttempt.objects.create(
        user=request.user,
        assessment_type=assessment_type,
        difficulty=difficulty,
        question_count=question_count,
        question_ids=[question["id"] for question in selected_questions],
    )

    return Response(
        {
            "attempt_id": str(attempt.id),
            "assessment_type": attempt.assessment_type,
            "difficulty": attempt.difficulty,
            "question_count": attempt.question_count,
            "questions": selected_questions,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def submit_assessment(request, attempt_id):
    # Lock the attempt while validating and saving its submission.
    # This helps prevent two simultaneous submissions for the same attempt.
    with transaction.atomic():
        attempt = get_object_or_404(
            AssessmentAttempt.objects.select_for_update(),
            id=attempt_id,
            user=request.user,
        )

        if attempt.status == AssessmentAttempt.Status.COMPLETED:
            return Response(
                {"error": "This assessment has already been submitted."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        answers = request.data.get("answers")

        if not isinstance(answers, dict):
            return Response(
                {
                    "error": (
                        "Answers must be an object mapping "
                        "question IDs to answer letters."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        selected_ids = attempt.question_ids

        # The saved attempt, not the request, defines the valid questions.
        if (
            not isinstance(selected_ids, list)
            or len(selected_ids) != attempt.question_count
            or len(set(selected_ids)) != len(selected_ids)
            or not all(
                isinstance(question_id, str)
                for question_id in selected_ids
            )
        ):
            return Response(
                {"error": "The saved assessment question list is invalid."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Do not allow answers for questions outside this attempt.
        if any(
            not isinstance(question_id, str)
            or question_id not in selected_ids
            for question_id in answers
        ):
            return Response(
                {
                    "error": (
                        "Answers contain a question not included "
                        "in this attempt."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Normalize answer letters and reject malformed values.
        normalized_answers = {}

        for question_id, answer in answers.items():
            if not isinstance(answer, str):
                return Response(
                    {
                        "error": (
                            f"Answer for question {question_id} "
                            "must be a letter from A to D."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            answer = answer.strip().upper()

            if answer not in {"A", "B", "C", "D"}:
                return Response(
                    {
                        "error": (
                            f"Invalid answer for question {question_id}. "
                            "Use A, B, C, or D."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            normalized_answers[question_id] = answer

        bank = get_question_bank()

        if any(question_id not in bank for question_id in selected_ids):
            return Response(
                {
                    "error": (
                        "One or more saved questions are missing "
                        "from the question bank."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = score_answers(selected_ids, normalized_answers)
        except ValueError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Persist every answer and the final score in the same transaction.
        # Missing answers remain unanswered and are scored as incorrect.
        for item in result["results"]:
            AssessmentAnswer.objects.update_or_create(
                attempt=attempt,
                question_id=item["question_id"],
                defaults={
                    "selected_answer": item["submitted_answer"] or "",
                    "is_correct": item["is_correct"],
                },
            )

            question = bank[item["question_id"]]
            item["question"] = question["question"]
            item["options"] = question["options"]

        attempt.correct_answers = result["correct_answers"]
        attempt.score_percentage = result["score_percentage"]
        attempt.status = AssessmentAttempt.Status.COMPLETED
        attempt.completed_at = timezone.now()

        attempt.save(
            update_fields=[
                "correct_answers",
                "score_percentage",
                "status",
                "completed_at",
            ]
        )

    # Return correct answers and explanations only after submission.
    return Response(
        {
            "attempt_id": str(attempt.id),
            "total_questions": result["total_questions"],
            "correct_answers": result["correct_answers"],
            "incorrect_or_unanswered": result["incorrect_or_unanswered"],
            "score_percentage": result["score_percentage"],
            "results": result["results"],
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def assessment_history(request):
    attempts = AssessmentAttempt.objects.filter(
        user=request.user
    ).order_by("-started_at")

    return Response(
        AssessmentAttemptSerializer(attempts, many=True).data,
        status=status.HTTP_200_OK,
    )
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def performance_summary(request):
    """
    Return performance analytics for the authenticated student.
    Only completed assessments are included.
    """
    attempts = AssessmentAttempt.objects.filter(
        user=request.user,
        status=AssessmentAttempt.Status.COMPLETED,
    )

    summary = attempts.aggregate(
        total_assessments=Count("id"),
        average_score=Avg("score_percentage"),
        highest_score=Max("score_percentage"),
        total_correct=Sum("correct_answers"),
        total_questions=Sum("question_count"),
    )

    total_assessments = summary["total_assessments"] or 0
    total_correct = summary["total_correct"] or 0
    total_questions = summary["total_questions"] or 0

    category_performance = []

    for assessment_type, label in AssessmentAttempt.AssessmentType.choices:
        category_attempts = attempts.filter(
            assessment_type=assessment_type
        )

        category_data = category_attempts.aggregate(
            attempts=Count("id"),
            average_score=Avg("score_percentage"),
            highest_score=Max("score_percentage"),
        )

        category_performance.append({
            "assessment_type": assessment_type,
            "label": label,
            "attempts": category_data["attempts"] or 0,
            "average_score": (
                round(float(category_data["average_score"]), 2)
                if category_data["average_score"] is not None
                else 0
            ),
            "highest_score": (
                round(float(category_data["highest_score"]), 2)
                if category_data["highest_score"] is not None
                else 0
            ),
        })

        
    difficulty_performance = []

    for assessment_type, label in AssessmentAttempt.AssessmentType.choices:
        for difficulty, difficulty_label in AssessmentAttempt.Difficulty.choices:
            difficulty_attempts = attempts.filter(
                assessment_type=assessment_type,
                difficulty=difficulty,
            )

            difficulty_data = difficulty_attempts.aggregate(
                attempts=Count("id"),
                average_score=Avg("score_percentage"),
            )

            difficulty_performance.append({
                "assessment_type": assessment_type,
                "category": label,
                "difficulty": difficulty,
                "difficulty_label": difficulty_label,
                "attempts": difficulty_data["attempts"] or 0,
                "average_score": (
                    round(float(difficulty_data["average_score"]), 2)
                    if difficulty_data["average_score"] is not None
                    else 0
                ),
            })
        

    recent_attempts = attempts.order_by("-completed_at")[:10]

    recent_results = [
        {
            "attempt_id": str(attempt.id),
            "assessment_type": attempt.assessment_type,
            "difficulty": attempt.difficulty,
            "question_count": attempt.question_count,
            "correct_answers": attempt.correct_answers,
            "score_percentage": float(attempt.score_percentage),
            "completed_at": attempt.completed_at,
        }
        for attempt in recent_attempts
    ]

    return Response({
        "summary": {
            "total_assessments": total_assessments,
            "average_score": (
                round(float(summary["average_score"]), 2)
                if summary["average_score"] is not None
                else 0
            ),
            "highest_score": (
                round(float(summary["highest_score"]), 2)
                if summary["highest_score"] is not None
                else 0
            ),
            "total_correct_answers": total_correct,
            "total_questions_answered_or_attempted": total_questions,
        },
        "category_performance": category_performance,
        "difficulty_performance": difficulty_performance,
        "recent_results": recent_results,
    }, status=status.HTTP_200_OK)