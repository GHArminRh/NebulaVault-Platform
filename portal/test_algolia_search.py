from django.test import SimpleTestCase

from portal.algolia_search import normalize_search_text


class PersianSearchNormalizationTests(SimpleTestCase):
    def test_normalizes_arabic_yeh_and_kaf(self):
        self.assertEqual(normalize_search_text("ي ك"), "ی ک")

    def test_normalizes_half_spaces_and_diacritics(self):
        self.assertEqual(normalize_search_text("نرم‌افزارِ  امن"), "نرم افزار امن")

    def test_collapses_whitespace(self):
        self.assertEqual(normalize_search_text("  Nebula   Vault  "), "Nebula Vault")
