from rest_framework import serializers
from .models import InterviewSession, InterviewQuestion, InterviewAnswer


class InterviewAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewAnswer
        fields = [
            "id",
            "answer_text",
            "score",
            "feedback",
            "strengths",
            "improvements",
            "submitted_at",
        ]
        read_only_fields = [
            "id",
            "score",
            "feedback",
            "strengths",
            "improvements",
            "submitted_at",
        ]


class InterviewQuestionSerializer(serializers.ModelSerializer):
    answer = serializers.SerializerMethodField()

    class Meta:
        model = InterviewQuestion
        fields = ["id", "question_text", "order", "max_score", "answer"]

    def get_answer(self, obj):
        answer = obj.answers.order_by("-submitted_at").first()
        if answer:
            return InterviewAnswerSerializer(answer).data
        return None


class InterviewSessionSerializer(serializers.ModelSerializer):
    questions = InterviewQuestionSerializer(many=True, read_only=True)

    class Meta:
        model = InterviewSession
        fields = [
            "id",
            "job_role",
            "interview_type",
            "difficulty",
            "status",
            "total_score",
            "created_at",
            "completed_at",
            "questions",
        ]
        read_only_fields = [
            "id",
            "status",
            "total_score",
            "created_at",
            "completed_at",
        ]