from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from catalog.rich_text import clean_rich_text
from comment.models import Comment

class BlogPost(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
    # Compatible with the comment package's PositiveIntegerField object_id.
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=220)
    slug = models.SlugField(max_length=240, unique=True, blank=True)
    excerpt = models.CharField(max_length=360, blank=True)
    content = models.TextField()
    cover_image = models.ImageField(upload_to="blog/covers/%Y/%m/", blank=True)
    category = models.CharField(max_length=80, blank=True, db_index=True)
    tags = models.CharField(max_length=240, blank=True, help_text="Comma-separated keywords")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT, db_index=True)
    is_featured = models.BooleanField(default=False, db_index=True)
    seo_title = models.CharField(max_length=220, blank=True)
    seo_description = models.CharField(max_length=320, blank=True)
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    comments = GenericRelation(Comment, related_query_name="blog_post")
    class Meta:
        ordering = ("-is_featured", "-published_at", "-created_at")
        verbose_name = "Blog post"
        verbose_name_plural = "Blog posts"
    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title, allow_unicode=True) or "article"
            candidate, suffix = base[:240], 2
            qs = type(self).objects.all()
            if self.pk: qs = qs.exclude(pk=self.pk)
            while qs.filter(slug=candidate).exists():
                tail = f"-{suffix}"; candidate = f"{base[:240-len(tail)]}{tail}"; suffix += 1
            self.slug = candidate
        self.content = clean_rich_text(self.content)
        if self.status == self.Status.PUBLISHED and self.published_at is None:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)
    @property
    def reading_minutes(self):
        from html import unescape
        from re import sub
        words = len(sub(r"\s+", " ", unescape(sub(r"<[^>]+>", " ", self.content))).split())
        return max(1, (words + 199) // 200)
    def __str__(self): return self.title
