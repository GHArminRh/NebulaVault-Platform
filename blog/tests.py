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
            list(revision.as_object().tags.values_list("pk", flat=True)),
            [tag.pk],
        )

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
