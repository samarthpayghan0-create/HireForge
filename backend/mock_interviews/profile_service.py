"""Fetch the student's profile from Member 1.

Two modes, chosen automatically:

* Merged project  -> the `dashboard` app is installed, so the profile is read
  directly from the database for the authenticated user.
* Standalone      -> the profile is requested over HTTP from a running
  Member 1 server, using the student's Member 1 token.
"""

import requests
from django.apps import apps
from django.conf import settings


class Member1ProfileError(Exception):
    pass


def _profile_from_database(user):
    from dashboard.models import StudentProfile
    from dashboard.serializers import StudentProfileSerializer

    profile, _ = StudentProfile.objects.get_or_create(user=user)
    return dict(StudentProfileSerializer(profile).data)


def _profile_from_member1_api(token):
    url = f"{settings.MEMBER1_API_BASE_URL.rstrip('/')}/profile/"

    try:
        response = requests.get(
            url,
            headers={"Authorization": f"Token {token}"},
            timeout=10,
        )
    except requests.RequestException as exc:
        raise Member1ProfileError(
            "Unable to connect to Member 1. Make sure its server is running."
        ) from exc

    if response.status_code in (401, 403):
        raise Member1ProfileError(
            "Member 1 rejected the authentication token. Please log in again."
        )

    if response.status_code != 200:
        raise Member1ProfileError(
            f"Member 1 profile request failed with status {response.status_code}."
        )

    try:
        profile = response.json()
    except ValueError as exc:
        raise Member1ProfileError(
            "Member 1 returned an invalid profile response."
        ) from exc

    if not isinstance(profile, dict):
        raise Member1ProfileError("Member 1 returned an unexpected profile format.")

    return profile


def get_student_profile(token=None, user=None):
    """Return the student's profile as a dict."""

    if user is not None and apps.is_installed("dashboard"):
        return _profile_from_database(user)

    if not token:
        raise Member1ProfileError(
            "A Member 1 authentication token is required to load the profile."
        )

    return _profile_from_member1_api(token)
