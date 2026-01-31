from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from workouts.models import Instructor


class RecommenderViewsTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(email="test@example.com", password="pass12345", is_active=True)
        self.client = Client()
        self.client.force_login(self.user)

    def test_recommender_page_renders(self):
        resp = self.client.get(reverse("recommender:index"))
        self.assertEqual(resp.status_code, 200)

    def test_suggest_endpoint_returns_json(self):
        Instructor.objects.create(name="Alex Toussaint")
        resp = self.client.get(reverse("recommender:suggest"), {"q": "Alex"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("results", data)
        self.assertTrue(any("Alex" in (r.get("name") or "") for r in data["results"]))

