from unittest import mock

from django.core.mail import EmailMultiAlternatives, send_mail
from django.test import TestCase, override_settings

BREVO = {"EMAIL_BACKEND": "apps.core.email_backends.BrevoEmailBackend", "BREVO_API_KEY": "key-123",
         "DEFAULT_FROM_EMAIL": "BorderlessTek Growth <team@example.com>"}


@override_settings(**BREVO)
class BrevoBackendTests(TestCase):
    @mock.patch("apps.core.email_backends.requests.post")
    def test_sends_through_api(self, post):
        post.return_value = mock.Mock(status_code=201, text="{}")
        msg = EmailMultiAlternatives("Hi", "Plain", None, ["Parent <p@example.com>"])
        msg.attach_alternative("<b>Hi</b>", "text/html")
        self.assertEqual(msg.send(), 1)
        kwargs = post.call_args.kwargs
        self.assertEqual(kwargs["headers"]["api-key"], "key-123")
        body = kwargs["json"]
        self.assertEqual(body["sender"], {"email": "team@example.com", "name": "BorderlessTek Growth"})
        self.assertEqual(body["to"], [{"email": "p@example.com", "name": "Parent"}])
        self.assertEqual((body["textContent"], body["htmlContent"]), ("Plain", "<b>Hi</b>"))

    @mock.patch("apps.core.email_backends.requests.post")
    def test_api_error_raises_unless_silent(self, post):
        post.return_value = mock.Mock(status_code=401, text="unauthorized")
        with self.assertRaises(RuntimeError):
            send_mail("Hi", "x", None, ["p@example.com"])
        self.assertEqual(send_mail("Hi", "x", None, ["p@example.com"], fail_silently=True), 0)
