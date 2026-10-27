from rest_framework import serializers

from .models import Resume, ResumeAnalysis

MAX_ROLE_LEN = 150
MAX_TITLE_LEN = 150
MIN_JD_CHARS = 40
MAX_JD_CHARS = 10_000


class ResumeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resume
        fields = ["id", "original_filename", "file_type", "file_size", "word_count", "created_at"]
        read_only_fields = fields


class ResumeAnalysisSummarySerializer(serializers.ModelSerializer):
    resume_filename = serializers.CharField(source="resume.original_filename", read_only=True)

    class Meta:
        model = ResumeAnalysis
        fields = [
            "id", "kind", "resume", "resume_filename", "target_role",
            "overall_score", "ats_score", "ai_used", "created_at",
        ]
        read_only_fields = fields


class ResumeAnalysisDetailSerializer(ResumeAnalysisSummarySerializer):
    class Meta(ResumeAnalysisSummarySerializer.Meta):
        fields = ResumeAnalysisSummarySerializer.Meta.fields + ["job_description", "result"]
        read_only_fields = fields


class AnalyzeRequestSerializer(serializers.Serializer):
    resume_id = serializers.IntegerField(min_value=1)
    target_role = serializers.CharField(max_length=MAX_ROLE_LEN, required=False, allow_blank=True, default="")
    use_ai = serializers.BooleanField(required=False, default=True)


class JobMatchRequestSerializer(serializers.Serializer):
    resume_id = serializers.IntegerField(min_value=1)
    job_title = serializers.CharField(max_length=MAX_TITLE_LEN, required=False, allow_blank=True, default="")
    job_description = serializers.CharField(max_length=MAX_JD_CHARS, trim_whitespace=True)
    use_ai = serializers.BooleanField(required=False, default=True)

    def validate_job_description(self, value):
        if len(value) < MIN_JD_CHARS:
            raise serializers.ValidationError(
                f"Please paste a fuller job description (at least {MIN_JD_CHARS} characters)."
            )
        return value
