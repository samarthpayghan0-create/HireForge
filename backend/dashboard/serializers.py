
from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import StudentProfile

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"},
    )
    full_name = serializers.CharField(
        write_only=True,
        max_length=150,
    )
    email = serializers.EmailField()

    class Meta:
        model = User
        fields = ["id", "email", "password", "full_name"]
        read_only_fields = ["id"]

    def validate_email(self, value):
        value = value.strip().lower()

        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "An account with this email already exists."
            )

        return value

    def create(self, validated_data):
        full_name = validated_data.pop("full_name")
        password = validated_data.pop("password")
        email = validated_data["email"]

        base_username = email.split("@")[0]
        username = base_username
        suffix = 1

        while User.objects.filter(username=username).exists():
            username = f"{base_username}_{suffix}"
            suffix += 1

        user = User(
            username=username,
            email=email,
        )
        user.set_password(password)
        user.save()

        StudentProfile.objects.create(
            user=user,
            full_name=full_name,
        )

        return user


class StudentProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentProfile
        fields = [
            "id",
            "full_name",
            "college_name",
            "degree",
            "graduation_year",
            "cgpa",
            "dsa_rating",
            "aptitude_rating",
            "communication_rating",
            "technical_skills",
            "projects",
            "internships",
            "certifications",
            "target_role",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
