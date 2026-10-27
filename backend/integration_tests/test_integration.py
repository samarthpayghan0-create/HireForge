"""Cross-module tests: these protect the *integration* of Members 1-4."""

import re
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest import skipUnless

from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from resume_career.tests import make_docx

PUBLIC = Path(settings.PUBLIC_DIR)
PASSWORD = "Passw0rd!xyz"


def register_and_login(client, email="asha@example.com", name="Asha Rao"):
    client.post("/api/register/", {"email": email, "password": PASSWORD, "full_name": name}, format="json")
    response = client.post("/api/login/", {"email": email, "password": PASSWORD}, format="json")
    assert response.status_code == 200, response.content
    client.credentials(HTTP_AUTHORIZATION="Token " + response.data["token"])
    return response.data["token"]


class HealthTests(TestCase):
    def test_health_endpoint_is_public_and_reports_database(self):
        response = APIClient().get("/api/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "database": "ok"})


class SingleLoginAcrossModulesTests(TestCase):
    """One token from Member 1's login must work for Members 2, 3 and 4."""

    def test_full_student_journey(self):
        client = APIClient()
        token = register_and_login(client)

        # Member 1: profile + readiness assessment needs a target role
        profile = client.patch(
            "/api/profile/",
            {"target_role": "Python Developer", "technical_skills": ["Python", "Django"], "projects": ["Task Tracker"]},
            format="json",
        )
        self.assertEqual(profile.status_code, 200)
        with mock.patch("dashboard.views.generate_readiness_assessment", return_value={"score": 70}):
            assessment = client.post("/api/assessment/")
        self.assertEqual(assessment.status_code, 200)
        self.assertEqual(client.get("/api/assessment/").data["assessment"], {"score": 70})

        # Member 2: take a 25-question DSA assessment and get a perfect score
        start = client.post(
            "/api/assessments/start/",
            {"assessment_type": "dsa", "difficulty": "medium", "question_count": 25},
            format="json",
        )
        self.assertEqual(start.status_code, 201)
        from assessments.questions import QUESTIONS

        bank = {q["id"]: q for q in QUESTIONS}
        answers = {q["id"]: bank[q["id"]]["correct_answer"] for q in start.data["questions"]}
        submit = client.post(f"/api/assessments/submit/{start.data['attempt_id']}/", {"answers": answers}, format="json")
        self.assertEqual(submit.status_code, 200)
        self.assertEqual(float(submit.data["score_percentage"]), 100.0)

        # Member 3: interview; the role comes from Member 1's profile (read from the DB, no 2nd token)
        with mock.patch("mock_interviews.question_generator.generate_json", side_effect=RuntimeError("no gemini")):
            interview = client.post("/api/interviews/sessions/", {"interview_type": "TECHNICAL", "difficulty": "EASY"}, format="json")
        self.assertEqual(interview.status_code, 201)
        self.assertEqual(interview.data["session"]["job_role"], "Python Developer")
        self.assertEqual(len(interview.data["session"]["questions"]), 10)

        # Member 4: resume upload + analysis; target role again from Member 1's profile
        upload = client.post("/api/resume/upload/", {"file": SimpleUploadedFile("cv.docx", make_docx())}, format="multipart")
        self.assertEqual(upload.status_code, 201)
        analysis = client.post("/api/resume/analyze/", {"resume_id": upload.data["resume"]["id"], "use_ai": False}, format="json")
        self.assertEqual(analysis.status_code, 201)
        self.assertEqual(analysis.data["target_role"], "Python Developer")

        # every module sees the same user
        self.assertEqual(len(client.get("/api/assessments/history/").data), 1)
        self.assertEqual(len(client.get("/api/resume/history/").data), 1)
        self.assertEqual(len(client.get("/api/interviews/sessions/").data), 1)
        self.assertTrue(token)


class SecurityAcrossModulesTests(TestCase):
    PROTECTED = [
        ("get", "/api/profile/"), ("get", "/api/assessment/"),
        ("post", "/api/assessments/start/"), ("get", "/api/assessments/history/"), ("get", "/api/assessments/performance/"),
        ("get", "/api/interviews/sessions/"), ("post", "/api/interviews/sessions/"),
        ("post", "/api/resume/upload/"), ("get", "/api/resume/resumes/"), ("post", "/api/resume/analyze/"),
        ("post", "/api/resume/job-match/"), ("get", "/api/resume/history/"),
    ]

    def test_every_protected_endpoint_requires_a_token(self):
        client = APIClient()
        for method, url in self.PROTECTED:
            with self.subTest(url=url):
                self.assertEqual(getattr(client, method)(url).status_code, 401)
        self.assertEqual(client.get("/api/profile/", HTTP_AUTHORIZATION="Token nonsense").status_code, 401)

    def test_users_cannot_see_each_others_data(self):
        alice, bob = APIClient(), APIClient()
        register_and_login(alice, "alice@example.com", "Alice")
        register_and_login(bob, "bob@example.com", "Bob")

        resume_id = alice.post("/api/resume/upload/", {"file": SimpleUploadedFile("a.docx", make_docx())}, format="multipart").data["resume"]["id"]
        with mock.patch("mock_interviews.question_generator.generate_json", side_effect=RuntimeError):
            session_id = alice.post("/api/interviews/sessions/", {"job_role": "Dev", "interview_type": "HR", "difficulty": "EASY"}, format="json").data["session"]["id"]
        attempt_id = alice.post("/api/assessments/start/", {"assessment_type": "aptitude", "difficulty": "medium", "question_count": 25}, format="json").data["attempt_id"]

        self.assertEqual(bob.post("/api/resume/analyze/", {"resume_id": resume_id}, format="json").status_code, 404)
        self.assertEqual(bob.delete(f"/api/resume/resumes/{resume_id}/").status_code, 404)
        self.assertEqual(bob.get(f"/api/interviews/sessions/{session_id}/").status_code, 404)
        self.assertEqual(bob.post(f"/api/assessments/submit/{attempt_id}/", {"answers": {}}, format="json").status_code, 404)
        self.assertEqual(bob.get("/api/resume/resumes/").data, [])
        self.assertEqual(bob.get("/api/interviews/sessions/").data, [])
        self.assertEqual(bob.get("/api/profile/").data["full_name"], "Bob")

    def test_api_responses_do_not_leak_answer_keys_before_submission(self):
        client = APIClient()
        register_and_login(client)
        start = client.post("/api/assessments/start/", {"assessment_type": "technical", "difficulty": "hard", "question_count": 25}, format="json")
        for question in start.data["questions"]:
            self.assertNotIn("correct_answer", question)
            self.assertNotIn("explanation", question)


@skipUnless(settings.SERVE_FRONTEND, "frontend is served by the CDN, not Django, in this configuration")
class FrontendServingTests(TestCase):
    def test_pages_are_served(self):
        for url in ("/", "/index.html", "/login.html", "/dashboard.html", "/assessments/", "/resume/", "/assessments/js/app.js", "/script.js"):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.get("/interview/").status_code, 200)

    def test_path_traversal_is_blocked(self):
        for url in ("/../backend/config/settings.py", "/..%2fbackend%2fconfig%2fsettings.py", "/assessments/../../backend/manage.py"):
            with self.subTest(url=url):
                self.assertIn(self.client.get(url).status_code, (301, 400, 404))

    def test_unknown_page_is_404(self):
        self.assertEqual(self.client.get("/nope.html").status_code, 404)


class FrontendStaticChecks(SimpleTestCase):
    """Static checks that keep the deployed pages working."""

    FILES = [p for p in PUBLIC.rglob("*") if p.suffix in {".html", ".js"}] + [
        Path(settings.BASE_DIR) / "mock_interviews" / "templates" / "mock_interviews" / "interview.html"
    ]

    def test_no_hardcoded_localhost_api_url_outside_dev_fallback(self):
        """A plain "http://127.0.0.1:8000" would break every page after deployment."""
        for path in self.FILES:
            text = path.read_text(encoding="utf-8")
            for match in re.finditer(r"127\.0\.0\.1:8000", text):
                context = text[max(0, match.start() - 160): match.start()]
                with self.subTest(file=path.name):
                    self.assertIn('"5500"', context, f"{path}: hard-coded localhost API URL")

    def test_internal_links_resolve(self):
        for page in PUBLIC.rglob("*.html"):
            html = page.read_text(encoding="utf-8")
            for target in re.findall(r'(?:href|src)="([^"#?]+)', html):
                if re.match(r"^(https?:|mailto:|tel:|data:|javascript:)", target):
                    continue
                if target.startswith("/"):
                    if target in {"/interview/"}:  # served by Django
                        continue
                    resolved = PUBLIC / target.lstrip("/")
                else:
                    resolved = (page.parent / target).resolve()
                with self.subTest(page=str(page.relative_to(PUBLIC)), target=target):
                    self.assertTrue(resolved.exists(), f"{page.name} links to missing {target}")

    def test_all_pages_share_the_same_token_key(self):
        for path in self.FILES:
            text = path.read_text(encoding="utf-8")
            if "hireforge" in text and "localStorage" in text:
                with self.subTest(file=path.name):
                    self.assertNotIn("hireforgeMember1Token", text)
