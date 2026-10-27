
from django.contrib.auth import authenticate, get_user_model

from rest_framework import generics, permissions, status
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView

from .gemini_service import (
    GeminiAssessmentError,
    generate_readiness_assessment,
)
from .models import ReadinessAssessment, StudentProfile
from .serializers import RegisterSerializer, StudentProfileSerializer


User = get_user_model()


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)

        return Response(
            {
                "message": "Registration successful.",
                "token": token.key,
                "username": user.get_username(),
                "email": user.email,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("email", "").strip().lower()
        password = request.data.get("password", "")

        if not email or not password:
            return Response(
                {"detail": "Email and password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user_record = User.objects.filter(
            email__iexact=email
        ).first()

        user = (
            authenticate(
                request,
                username=user_record.get_username(),
                password=password,
            )
            if user_record
            else None
        )

        if user is None:
            return Response(
                {"detail": "Invalid email or password."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        token, _ = Token.objects.get_or_create(user=user)

        return Response(
            {
                "token": token.key,
                "username": user.get_username(),
                "email": user.email,
            }
        )


class StudentProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = StudentProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        profile, _ = StudentProfile.objects.get_or_create(
            user=self.request.user
        )
        return profile


class ReadinessAssessmentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # Retrieve the latest saved assessment for this user.
        saved = ReadinessAssessment.objects.filter(
            user=request.user
        ).first()

        if saved is None:
            return Response(
                {
                    "assessment": None,
                    "disclaimer": (
                        "No saved assessment exists yet. "
                        "Generate your first assessment."
                    ),
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                "message": "Saved assessment retrieved successfully.",
                "assessment": saved.assessment,
                "disclaimer": saved.disclaimer,
                "created_at": saved.created_at,
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        profile, _ = StudentProfile.objects.get_or_create(
            user=request.user
        )

        if not profile.target_role or not profile.target_role.strip():
            return Response(
                {
                    "detail": (
                        "Set your target role in your student profile "
                        "before requesting an assessment."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            assessment = generate_readiness_assessment(profile)
        except GeminiAssessmentError as exc:
            print("READINESS ASSESSMENT ERROR:", str(exc))
            return Response(
            {"detail": str(exc)},
            status=status.HTTP_502_BAD_GATEWAY,
    )

        disclaimer = (
            "This AI-generated score is an indicative preparation "
            "assessment based on the profile information provided. "
            "It is not a validated probability of getting hired "
            "or placed."
        )

        # Save the assessment in MySQL for future logins.
        saved = ReadinessAssessment.objects.create(
            user=request.user,
            assessment=assessment,
            disclaimer=disclaimer,
        )

        return Response(
            {
                "message": "Skill-gap analysis generated successfully.",
                "assessment": saved.assessment,
                "disclaimer": saved.disclaimer,
                "created_at": saved.created_at,
            },
            status=status.HTTP_200_OK,
        )
