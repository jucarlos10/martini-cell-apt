from django.test import SimpleTestCase, override_settings
from django.urls import reverse


class HealthTests(SimpleTestCase):
    def test_get_is_public_and_has_no_customer_data(self):
        response = self.client.get(reverse("api-health"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        self.assertEqual(response["Cache-Control"], "no-store")

    def test_post_is_not_allowed(self):
        response = self.client.post(reverse("api-health"))
        self.assertEqual(response.status_code, 405)

    @override_settings(
        ALLOWED_HOSTS=["host.example"],
        SECURE_SSL_REDIRECT=True,
        SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO", "https"),
    )
    def test_proxy_https_is_recognized_without_redirect_loop(self):
        url = reverse("api-health")
        secure_response = self.client.get(
            url,
            HTTP_HOST="host.example",
            HTTP_X_FORWARDED_PROTO="https",
        )
        self.assertEqual(secure_response.status_code, 200)

        plain_response = self.client.get(url, HTTP_HOST="host.example")
        self.assertEqual(plain_response.status_code, 301)
        self.assertEqual(plain_response["Location"], "https://host.example/api/health/")
