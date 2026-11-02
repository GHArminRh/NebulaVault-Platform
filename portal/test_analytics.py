from django.test import TestCase, override_settings
from django.urls import reverse


class AnalyticsConsentTests(TestCase):
    @override_settings(GA4_MEASUREMENT_ID="G-TEST123456")
    def test_ga4_tag_is_present_but_consent_is_not_assumed(self):
        response = self.client.get(reverse("portal:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-ga4-id="G-TEST123456"')
        self.assertContains(response, 'id="nv-analytics-consent"')
        self.assertContains(response, "data-ga4-accept")
        self.assertContains(response, "data-ga4-reject")
        self.assertContains(response, "portal/js/ga4.js")

    @override_settings(GA4_MEASUREMENT_ID="")
    def test_ga4_is_disabled_without_a_measurement_id(self):
        response = self.client.get(reverse("portal:home"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "portal/js/ga4.js")
        self.assertNotContains(response, 'id="nv-analytics-consent"')

    @override_settings(GA4_MEASUREMENT_ID="G-TEST123456")
    def test_server_confirmed_auth_event_is_exposed_only_once(self):
        session = self.client.session
        session["ga4_pending_event"] = "login"
        session.save()

        first_response = self.client.get(reverse("portal:home"))
        second_response = self.client.get(reverse("portal:home"))

        self.assertContains(first_response, 'data-ga4-pending-event="login"')
        self.assertContains(second_response, 'data-ga4-pending-event=""')


