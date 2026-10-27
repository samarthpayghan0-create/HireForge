
from rest_framework import serializers

from .models import AssessmentAnswer, AssessmentAttempt


class AssessmentAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssessmentAttempt
        fields = [
            "id",
            "assessment_type",
            "difficulty",
            "question_count",
            "status",
            "correct_answers",
            "score_percentage",
            "started_at",
            "completed_at",
        ]
        read_only_fields = fields


class AssessmentAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssessmentAnswer
        fields = [
            "question_id",
            "selected_answer",
            "is_correct",
        ]
        read_only_fields = fields
