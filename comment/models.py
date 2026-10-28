import secrets
import string
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from accounts.models import Customer

def make_urlhash():
    return "".join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(12))

class CommentSettings(models.Model):
    name = models.CharField(max_length=30, default="Nebula Vault Blog")
    slug = models.SlugField(primary_key=True, default="default-config")
    content_words_count = models.PositiveSmallIntegerField(default=40)
    status_check = models.BooleanField(default=True)
    status_edited_check = models.BooleanField(default=True)
    allow_spoiler = models.BooleanField(default=True)
    allow_reply = models.BooleanField(default=True)
    allow_edit = models.BooleanField(default=True)
    allow_delete = models.BooleanField(default=True)
    allow_reaction = models.BooleanField(default=True)
    per_page = models.PositiveSmallIntegerField(default=10)
    theme_direction = models.CharField(max_length=3, default="rtl")
    theme_dark_mode = models.BooleanField(default=True)
    class Meta:
        verbose_name = "Comment settings"
        verbose_name_plural = "Comment settings"
    def __str__(self): return self.name

class Comment(models.Model):
    class Status(models.TextChoices):
        DELIVERED = "d", "Pending review"
        ACCEPTED = "a", "Accepted"
        REJECTED = "r", "Rejected"
    user = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="comments")
    content_main = models.TextField()
    content = models.TextField()
    parent = models.ForeignKey("self", on_delete=models.CASCADE, related_name="children", null=True, blank=True)
    is_spoiler = models.BooleanField(default=False)
    is_pinned = models.BooleanField(default=False)
    status = models.CharField(max_length=1, choices=Status.choices, default=Status.DELIVERED, db_index=True)
    status_edited = models.CharField(max_length=1, choices=(("n","None"),("d","Pending review"),("a","Accepted"),("r","Rejected")), default="n")
    urlhash = models.CharField(max_length=50, unique=True, editable=False, default=make_urlhash)
    posted = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    class Meta:
        ordering = ("-is_pinned", "-posted")
        verbose_name = "Comment"
        verbose_name_plural = "Comments"
    def __str__(self): return self.content_main[:80]
    @property
    def is_parent(self): return self.parent_id is None

class React(models.Model):
    slug = models.CharField(max_length=20, unique=True)
    emoji = models.CharField(max_length=5)
    def __str__(self): return self.slug

class Reaction(models.Model):
    user = models.ForeignKey(Customer, related_name="comment_reactions", on_delete=models.CASCADE)
    comment = models.ForeignKey(Comment, related_name="reactions", on_delete=models.CASCADE)
    react = models.ForeignKey(React, related_name="reactions", on_delete=models.CASCADE)
    class Meta:
        constraints = [models.UniqueConstraint(fields=("user","comment"), name="comment_one_reaction_per_user")]
    def __str__(self): return f"{self.user} · {self.react.slug}"
