from types import SimpleNamespace
from uuid import uuid4

from django.test import SimpleTestCase

from billing.views import _ga4_purchase_payload


class GA4PurchasePayloadTests(SimpleTestCase):
    def test_toman_order_is_normalized_to_irr_without_customer_data(self):
        line = SimpleNamespace(
            plan_id=uuid4(),
            plan_name="Annual",
            product_name="Nebula Desktop",
            amount_minor_units=250000,
        )

        class ItemCollection:
            def select_related(self, *_args):
                return self

            def all(self):
                return [line]

        order = SimpleNamespace(
            order_number=uuid4(),
            amount_minor_units=250000,
            currency="IRT",
            items=ItemCollection(),
        )

        payload = _ga4_purchase_payload(order)

        self.assertEqual(payload["currency"], "IRR")
        self.assertEqual(payload["value"], 25000.0)
        self.assertEqual(payload["items"][0]["price"], 25000.0)
        self.assertEqual(payload["items"][0]["item_name"], "Annual")
        self.assertEqual(
            set(payload),
            {"transaction_id", "value", "currency", "items"},
        )
        self.assertNotIn("email", payload)
        self.assertNotIn("user_id", payload)
        self.assertNotIn("license_key", payload)

    def test_rial_order_uses_iso_currency_and_hundredth_unit_conversion(self):
        class EmptyItems:
            def select_related(self, *_args):
                return self

            def all(self):
                return []

        plan = SimpleNamespace(
            pk=uuid4(),
            name="Monthly",
            product=SimpleNamespace(name="Nebula Desktop"),
        )
        order = SimpleNamespace(
            order_number=uuid4(),
            amount_minor_units=125000,
            currency="IRR",
            items=EmptyItems(),
            plan=plan,
        )

        payload = _ga4_purchase_payload(order)

        self.assertEqual(payload["currency"], "IRR")
        self.assertEqual(payload["value"], 1250.0)
        self.assertEqual(payload["items"][0]["price"], 1250.0)

