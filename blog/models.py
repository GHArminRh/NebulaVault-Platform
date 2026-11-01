import uuid

from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django_resized import ResizedImageField
from modelcluster.fields import ParentalManyToManyField
from modelcluster.models import ClusterableModel
from wagtail.models import DraftStateMixin, PreviewableMixin, RevisionMixin

from accounts.models import Customer
from catalog.rich_text import clean_rich_text
from comment.models import Comment
from rating.models import Rating


class Tag(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, unique=True)

    class Meta:
        ordering = ("name",)
        verbose_name = "Blog tag"
        verbose_name_plural = "Blog tags"

    def __str__(self):
        return self.name


class BlogPost(DraftStateMixin, RevisionMixin, PreviewableMixin, ClusterableModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"

    # Keep the integer database primary key because both the existing comment
    # system and django-rating-system use PositiveIntegerField generic object IDs.
    # A UUID public identifier is also provided for integrations and APIs.
    id = models.AutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    title = models.CharField(max_length=220)
    slug = models.SlugField(max_length=240, unique=True, blank=True)
    excerpt = models.CharField(max_length=360, blank=True)
    content = models.TextField()
    img = ResizedImageField(
        upload_to="blog/covers/%Y/%m/",
        size=[1600, 900],
        quality=88,
        force_format="WEBP",
        blank=True,
    )
    category = models.CharField(max_length=80, blank=True, db_index=True)
    tags = ParentalManyToManyField(Tag, blank=True, related_name="posts")
    live = models.BooleanField(default=False, editable=False)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT, db_index=True)
    is_featured = models.BooleanField(default=False, db_index=True)
    seo_title = models.CharField(max_length=220, blank=True)
    seo_description = models.CharField(max_length=320, blank=True)
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    comments = GenericRelation(Comment, related_query_name="blog_post")
    ratings = GenericRelation(Rating, related_query_name="blog_post_rating")

    class Meta:
        ordering = ("-is_featured", "-published_at", "-created_at")
        verbose_name = "Blog post"
        verbose_name_plural = "Blog posts"
        permissions = (("vip", "VIP"), ("common", "COMMON"))

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title, allow_unicode=True) or "article"
            candidate, suffix = base[:240], 2
            qs = type(self).objects.all()
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            while qs.filter(slug=candidate).exists():
                tail = f"-{suffix}"
                candidate = f"{base[:240-len(tail)]}{tail}"
                suffix += 1
            self.slug = candidate
        self.content = clean_rich_text(self.content)
        if self.status == self.Status.PUBLISHED and self.published_at is None:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    @property
    def cover_image(self):
        """Backward-compatible alias used by older templates."""
        return self.img

    @property
    def reading_minutes(self):
        from html import unescape
        from re import sub
        words = len(sub(r"\\s+", " ", unescape(sub(r"<[^>]+>", " ", self.content))).split())
        return max(1, (words + 199) // 200)

    def get_preview_template(self, request, mode_name):
        return "blog/post_preview.html"

    def publish(
        self,
        revision,
        user=None,
        changed=True,
        log_action=True,
        previous_revision=None,
        skip_permission_checks=False,
    ):
        result = super().publish(
            revision,
            user=user,
            changed=changed,
            log_action=log_action,
            previous_revision=previous_revision,
            skip_permission_checks=skip_permission_checks,
        )
        self.refresh_from_db()
        if self.status != self.Status.PUBLISHED or not self.published_at:
            self.status = self.Status.PUBLISHED
            if not self.published_at:
                self.published_at = timezone.now()
            self.save(update_fields=["status", "published_at"])
        return result

    def unpublish(self, set_expired=False, commit=True, user=None, log_action=True):
        result = super().unpublish(
            set_expired=set_expired,
            commit=commit,
            user=user,
            log_action=log_action,
        )
        if commit:
            self.refresh_from_db()
            if self.status != self.Status.DRAFT:
                self.status = self.Status.DRAFT
                self.save(update_fields=["status"])
        return result

    def __str__(self):
        return self.title


# Keep existing imports and integrations working while the model's public
# vocabulary can match the concise Post name used in documentation.
Post = BlogPost


class BlogPostRating(models.Model):
    """One customer rating per article; separate from staff-only package ratings."""
    post = models.ForeignKey(BlogPost, on_delete=models.CASCADE, related_name="customer_ratings")
    user = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="blog_post_ratings")
    score = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)
        constraints = [
            models.UniqueConstraint(fields=("post", "user"), name="blog_post_rating_once_per_customer"),
            models.CheckConstraint(condition=models.Q(score__gte=1, score__lte=5), name="blog_post_rating_score_1_5"),
        ]

    def __str__(self):
        return f"{self.post} · {self.score}/5"
