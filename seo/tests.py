from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from .models import SEOAuditIssue, SEOAuditRun


class SEOAuditModelTests(TestCase):
    def test_audit_run_records_requested_by_and_counters(self):
        staff = get_user_model().objects.create_user(
            username="seo-auditor",
            password="test-password",
        )
        run = SEOAuditRun.objects.create(requested_by=staff, pages_scanned=4)

        self.assertEqual(run.status, SEOAuditRun.Status.QUEUED)
        self.assertEqual(run.pages_scanned, 4)
        self.assertEqual(run.requested_by, staff)

    def test_issue_is_unique_per_run_url_and_code(self):
        run = SEOAuditRun.objects.create()
        issue_data = {
            "run": run,
            "url": "https://mydigigi.ir/example/",
            "code": "missing-title",
            "severity": SEOAuditIssue.Severity.ERROR,
            "title": "Page has no title",
        }
        SEOAuditIssue.objects.create(**issue_data)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                SEOAuditIssue.objects.create(**issue_data)
