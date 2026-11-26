from datetime import timedelta
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from .activity import today
from .models import PageActivity


class ActivityTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client(enforce_csrf_checks=True)
        self.client.get(reverse("intake"))
        self.url = reverse("page_activity")
        self.token = self.client.cookies["csrftoken"].value

    def post(self, **overrides):
        data = {"page": "guided", "event": "clicks", "count": 4, **overrides}
        return self.client.post(self.url, urlencode(data),
                                content_type="application/x-www-form-urlencoded",
                                HTTP_X_CSRFTOKEN=self.token)

    def test_aggregate_and_minimize(self):
        for payload in [{}, {}, {"event": "helpful", "count": 1}]:
            self.assertEqual(self.post(**payload).status_code, 204)
        bucket = PageActivity.objects.get()
        self.assertEqual((bucket.page, bucket.clicks, bucket.helpful), ("guided", 8, 1))
        for invalid in [{"page": "/review/private-token"}, {"label": "private"},
                        {"event": "helpful"}, {"count": 101}, {"count": -1}]:
            self.assertEqual(self.post(**invalid).status_code, 400)
        self.assertEqual(self.client.post(self.url).status_code, 403)

    def test_admin_access_and_reporting_window(self):
        report = reverse("admin:map_pageactivity_changelist")
        self.assertEqual(self.client.get(report).status_code, 302)
        user = get_user_model().objects.create_user("reviewer", is_staff=True)
        self.client.force_login(user)
        self.assertEqual(self.client.get(report).status_code, 403)
        user.user_permissions.add(Permission.objects.get(codename="view_pageactivity"))
        PageActivity.objects.create(page="guided", day=today() - timedelta(days=2), clicks=17)
        self.assertEqual(self.client.get(report).context["totals"]["clicks"], 17)
        self.assertEqual(self.client.get(report, {"days": 1}).context["totals"]["clicks"], 0)
        self.assertContains(self.client.get(report), "Resource map")

    def test_optional_questionnaire_note(self):
        url = reverse("questionnaire")
        data = {"csrfmiddlewaretoken": self.token, "food_today": "ongoing"}
        self.assertTemplateUsed(self.client.post(url, data), "map_recommended.html")
        response = self.client.post(url, {**data, "need_text": "I need a dentist"})
        self.assertContains(response, "From your written details")
        self.assertTrue(response.context["note_result"]["matches"])
        self.assertContains(response, "Was this page helpful?")
        self.assertTemplateUsed(self.client.post(url, {**data, "need_text": "in immediate danger"}), "crisis.html")
