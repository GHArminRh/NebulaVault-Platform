from django.test import TestCase
from django.utils import timezone

from wagtail.models import DraftStateMixin, PreviewableMixin, RevisionMixin

from .models import BlogPost, Tag


class BlogPostWagtailEditorialTests(TestCase):
    def test_blog_posts_support_drafts_revisions_and_preview(self):
        tag = Tag.objects.create(name="آموزشی")
        post = BlogPost.objects.create(
            title="مقاله آزمایشی",
            slug="wagtail-editorial-test",
            excerpt="معرفی مقاله",
            content="<p>متن مقاله</p>",
            status=BlogPost.Status.DRAFT,
        )
        post.tags.add(tag)

        self.assertIsInstance(post, DraftStateMixin)
        self.assertIsInstance(post, RevisionMixin)
        self.assertIsInstance(post, PreviewableMixin)
        self.assertFalse(post.live)
        self.assertEqual(post.get_preview_template(None, ""), "blog/post_preview.html")

        revision = post.save_revision()
        post.refresh_from_db()
        self.assertEqual(post.latest_revision_id, revision.pk)
        self.assertTrue(post.has_unpublished_changes)
        self.assertEqual(
            list(revision.as_object().tags.values_list("id", flat=True)),
            [tag.pk],
        )

    def test_saving_a_draft_does_not_replace_the_live_article(self):
        original_content = "<p>نسخه منتشرشده</p>"
        post = BlogPost.objects.create(
            title="مقاله منتشرشده",
            slug="wagtail-live-draft-test",
            content=original_content,
            status=BlogPost.Status.PUBLISHED,
            live=True,
        )
        post.content = "<p>نسخه پیش‌نویس جدید</p>"
        revision = post.save_revision()
        post.refresh_from_db()

        self.assertTrue(post.live)
        self.assertTrue(post.has_unpublished_changes)
        self.assertEqual(post.content, original_content)
        self.assertEqual(revision.as_object().content, "<p>نسخه پیش‌نویس جدید</p>")

    def test_publishing_revision_updates_legacy_publication_fields(self):
        post = BlogPost.objects.create(
            title="مقاله قابل انتشار",
            slug="wagtail-publish-test",
            content="<p>متن مقاله</p>",
            status=BlogPost.Status.DRAFT,
        )
        revision = post.save_revision()

        post.publish(revision, skip_permission_checks=True)
        post.refresh_from_db()

        self.assertTrue(post.live)
        self.assertEqual(post.status, BlogPost.Status.PUBLISHED)
        self.assertIsNotNone(post.published_at)
        self.assertIsNotNone(post.first_published_at)
        self.assertIsNotNone(post.last_published_at)
        self.assertLessEqual(post.published_at, timezone.now())

    def test_unpublishing_revision_preserves_existing_post_record(self):
        post = BlogPost.objects.create(
            title="مقاله برای لغو انتشار",
            slug="wagtail-unpublish-test",
            content="<p>متن مقاله</p>",
            status=BlogPost.Status.PUBLISHED,
        )
        revision = post.save_revision()
        post.publish(revision, skip_permission_checks=True)
        post.refresh_from_db()

        post.unpublish()
        post.refresh_from_db()

        self.assertFalse(post.live)
        self.assertEqual(post.status, BlogPost.Status.DRAFT)
        self.assertTrue(BlogPost.objects.filter(pk=post.pk).exists())



class BlogPostImageUploaderTests(TestCase):
    def test_admin_image_field_uses_nebula_uploader(self):
        from .forms import BlogPostAdminForm
        from portal.widgets import NebulaImageUploaderWidget

        form = BlogPostAdminForm()
        self.assertIsInstance(form.fields["img"].widget, NebulaImageUploaderWidget)
        rendered = str(form["img"])
        self.assertIn("data-nv-image-uploader", rendered)
        self.assertIn("data-dropzone", rendered)
        self.assertIn("data-upload-panel", rendered)

    def test_admin_image_upload_rejects_files_over_size_limit(self):
        from io import BytesIO
        from unittest.mock import patch

        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.core.exceptions import ValidationError
        from PIL import Image

        from portal.widgets import MAX_IMAGE_UPLOAD_BYTES

        image_buffer = BytesIO()
        Image.new("RGB", (2, 2), color="blue").save(image_buffer, format="PNG")
        image_bytes = image_buffer.getvalue()
        uploaded = SimpleUploadedFile(
            "oversized.png",
            image_bytes,
            content_type="image/png",
        )
        form = BlogPostAdminForm(
            data={
                "title": "Image upload limit test",
                "slug": "image-upload-limit-test",
                "content": "Test",
                "status": BlogPost.Status.DRAFT,
            },
            files={"img": uploaded},
        )
        with patch("portal.widgets.MAX_IMAGE_UPLOAD_BYTES", len(image_bytes) - 1):
            self.assertFalse(form.is_valid())
            self.assertIn("img", form.errors)
