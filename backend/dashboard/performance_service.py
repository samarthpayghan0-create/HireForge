from django.db.models import Avg

from assessments_api.models import AssessmentAttempt
from mock_interviews.models import InterviewSession


def get_student_performance(user):
    completed_assessments = AssessmentAttempt.objects.filter(
        user=user,
        status=AssessmentAttempt.Status.COMPLETED,
    )

    assessment_summary = {}

    for assessment_type, label in AssessmentAttempt.AssessmentType.choices:
        scores = completed_assessments.filter(
            assessment_type=assessment_type
        ).aggregate(average=Avg("score_percentage"))

        average = scores["average"]

        assessment_summary[assessment_type] = {
            "label": label,
            "attempts": completed_assessments.filter(
                assessment_type=assessment_type
            ).count(),
            "average_score": (
                round(float(average), 2)
                if average is not None
                else None
            ),
        }

    completed_interviews = InterviewSession.objects.filter(
        user_id=str(user.pk),
        status="COMPLETED",
    )

    interview_average = completed_interviews.aggregate(
        average=Avg("total_score")
    )["average"]

    return {
        "assessments": assessment_summary,
        "interview_count": completed_interviews.count(),
        "interview_average_out_of_10": (
            round(float(interview_average), 2)
            if interview_average is not None
            else None
        ),
    }
