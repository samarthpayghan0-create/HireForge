
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from assessments.questions import QUESTIONS
from .models import AssessmentAnswer, AssessmentAttempt


User = get_user_model()


class AssessmentAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="student_test",
            password="TestPassword!938",
        )
        cls.other_user = User.objects.create_user(
            username="other_student",
            password="OtherPassword!938",
        )

        cls.token = Token.objects.create(user=cls.user)

    def setUp(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {self.token.key}"
        )

    def start_assessment(self, username=None, **overrides):
        payload = {
            "assessment_type": "aptitude",
            "difficulty": "medium",
            "question_count": 25,
        }
        payload.update(overrides)

        return self.client.post(
            reverse("start-assessment"),
            payload,
            format="json",
        )

    def test_start_requires_authentication(self):
        self.client.credentials()

        response = self.client.post(
            reverse("start-assessment"),
            {
                "assessment_type": "aptitude",
                "difficulty": "medium",
                "question_count": 25,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_start_assessment_returns_questions_without_answers(self):
        response = self.start_assessment()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("attempt_id", response.data)
        self.assertEqual(len(response.data["questions"]), 25)

        for question in response.data["questions"]:
            self.assertNotIn("correct_answer", question)
            self.assertNotIn("explanation", question)

        attempt = AssessmentAttempt.objects.get(
            id=response.data["attempt_id"]
        )
        self.assertEqual(attempt.user, self.user)
        self.assertEqual(
            attempt.status,
            AssessmentAttempt.Status.IN_PROGRESS,
        )

    def test_invalid_assessment_parameters_are_rejected(self):
        response = self.start_assessment(
            assessment_type="invalid",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_submit_saves_score_and_answers(self):
        start_response = self.start_assessment()
        self.assertEqual(
            start_response.status_code,
            status.HTTP_201_CREATED,
        )

        attempt_id = start_response.data["attempt_id"]
        questions = start_response.data["questions"]

        answers = {
            question["id"]: "A"
            for question in questions
        }

        response = self.client.post(
            reverse(
                "submit-assessment",
                kwargs={"attempt_id": attempt_id},
            ),
            {"answers": answers},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_questions"], 25)

        attempt = AssessmentAttempt.objects.get(id=attempt_id)
        self.assertEqual(
            attempt.status,
            AssessmentAttempt.Status.COMPLETED,
        )
        self.assertEqual(
            AssessmentAnswer.objects.filter(attempt=attempt).count(),
            25,
        )
        self.assertEqual(
            attempt.correct_answers,
            response.data["correct_answers"],
        )

    def test_invalid_answer_letter_is_rejected(self):
        start_response = self.start_assessment()
        attempt_id = start_response.data["attempt_id"]
        question_id = start_response.data["questions"][0]["id"]

        response = self.client.post(
            reverse(
                "submit-assessment",
                kwargs={"attempt_id": attempt_id},
            ),
            {"answers": {question_id: "Z"}},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        attempt = AssessmentAttempt.objects.get(id=attempt_id)
        self.assertEqual(
            attempt.status,
            AssessmentAttempt.Status.IN_PROGRESS,
        )

    def test_duplicate_submission_is_rejected(self):
        start_response = self.start_assessment()
        attempt_id = start_response.data["attempt_id"]

        answers = {
            question["id"]: "A"
            for question in start_response.data["questions"]
        }

        url = reverse(
            "submit-assessment",
            kwargs={"attempt_id": attempt_id},
        )

        first_response = self.client.post(
            url,
            {"answers": answers},
            format="json",
        )
        second_response = self.client.post(
            url,
            {"answers": answers},
            format="json",
        )

        self.assertEqual(
            first_response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            second_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_user_cannot_access_another_users_attempt(self):
        start_response = self.start_assessment()
        attempt_id = start_response.data["attempt_id"]

        self.client.force_authenticate(user=self.other_user)

        response = self.client.post(
            reverse(
                "submit-assessment",
                kwargs={"attempt_id": attempt_id},
            ),
            {"answers": {}},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_history_contains_only_current_users_attempts(self):
        own_response = self.start_assessment()
        own_attempt_id = own_response.data["attempt_id"]

        self.client.force_authenticate(user=self.other_user)
        self.start_assessment()

        self.client.force_authenticate(user=self.user)

        response = self.client.get(reverse("assessment-history"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        returned_ids = {str(item["id"]) for item in response.data}
        self.assertIn(own_attempt_id, returned_ids)
        self.assertEqual(len(returned_ids), 1)

    def test_performance_summary_counts_completed_attempts_only(self):
        start_response = self.start_assessment()
        attempt_id = start_response.data["attempt_id"]

        attempt = AssessmentAttempt.objects.get(id=attempt_id)
        attempt.status = AssessmentAttempt.Status.COMPLETED
        attempt.correct_answers = 10
        attempt.score_percentage = 40
        attempt.save(
            update_fields=[
                "status",
                "correct_answers",
                "score_percentage",
            ]
        )

        response = self.client.get(reverse("performance-summary"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["summary"]["total_assessments"],
            1,
        )
        self.assertEqual(
            float(response.data["summary"]["average_score"]),
            40.0,
        )

    def test_performance_summary_excludes_other_users(self):
        response = self.start_assessment()
        attempt_id = response.data["attempt_id"]

        attempt = AssessmentAttempt.objects.get(id=attempt_id)
        attempt.status = AssessmentAttempt.Status.COMPLETED
        attempt.score_percentage = 80
        attempt.save(update_fields=["status", "score_percentage"])

        self.client.force_authenticate(user=self.other_user)

        response = self.client.get(reverse("performance-summary"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["summary"]["total_assessments"],
            0,
        )


class QuestionBankIntegrityTests(APITestCase):
    """Guards against the answer-key problems found in the original bank."""

    def test_ids_are_unique(self):
        ids = [q["id"] for q in QUESTIONS]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_question_is_well_formed(self):
        for q in QUESTIONS:
            with self.subTest(question=q["id"]):
                self.assertEqual(len(q["options"]), 4)
                self.assertEqual(len(set(q["options"])), 4)
                self.assertIn(q["correct_answer"], ["A", "B", "C", "D"])
                self.assertTrue(q["explanation"].strip())
                # The frontend adds the A/B/C/D labels itself.
                for option in q["options"]:
                    self.assertNotRegex(option, r"^[A-D][.)]\s")

    def test_each_category_can_supply_50_questions(self):
        from collections import Counter
        counts = Counter(
            (q["id"].split("_")[0], q["difficulty"]) for q in QUESTIONS
        )
        for key, count in counts.items():
            with self.subTest(category=key):
                self.assertGreaterEqual(count, 50)

    def test_correct_answer_position_is_not_predictable(self):
        from collections import Counter
        for prefix in ("apt", "dsa", "tech"):
            keys = Counter(
                q["correct_answer"]
                for q in QUESTIONS
                if q["id"].startswith(prefix)
            )
            with self.subTest(category=prefix):
                for letter in "ABCD":
                    share = keys[letter] / sum(keys.values())
                    self.assertGreater(share, 0.15)
                    self.assertLess(share, 0.35)

    def test_known_corrected_answers(self):
        bank = {q["id"]: q for q in QUESTIONS}
        expected = {
            "apt_hard_329": "25",
            "apt_hard_330": "60 kg",
            "apt_hard_399": "52",
            "apt_hard_322": "32",
            "apt_hard_326": "44.25",
        }
        for qid, text in expected.items():
            q = bank[qid]
            picked = q["options"]["ABCD".index(q["correct_answer"])]
            self.assertEqual(picked, text, qid)
