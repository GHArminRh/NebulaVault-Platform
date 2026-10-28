import uuid

import django_resized
import django.db.models.deletion
from django.db import migrations, models


def migrate_legacy_tags(apps, schema_editor):
    BlogPost = apps.get_model("blog", "BlogPost")
    Tag = apps.get_model("blog", "Tag")
    alias = schema_editor.connection.alias
    for post in BlogPost.objects.using(alias).all().iterator():
        raw_tags = getattr(post, "legacy_tags", "") or ""
        names = []
        for value in raw_tags.split(","):
            name = value.strip()
            if name and name not in names:
                names.append(name[:200])
        for name in names:
            tag, _ = Tag.objects.using(alias).get_or_create(name=name)
            post.tags.add(tag)


def populate_post_uuids(apps, schema_editor):
    BlogPost = apps.get_model("blog", "BlogPost")
    alias = schema_editor.connection.alias
    for post in BlogPost.objects.using(alias).filter(uuid__isnull=True).iterator():
        post.uuid = uuid.uuid4()
        post.save(update_fields=["uuid"])


class Migration(migrations.Migration):
    dependencies = [
        ("blog", "0001_initial"),
        ("rating", "0001_initial"),
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="blogpost",
            name="uuid",
            field=models.UUIDField(default=uuid.uuid4, editable=False, null=True),
        ),
        migrations.RunPython(populate_post_uuids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="blogpost",
            name="uuid",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.RenameField(
            model_name="blogpost",
            old_name="cover_image",
            new_name="img",
        ),
        migrations.AlterField(
            model_name="blogpost",
            name="img",
            field=django_resized.forms.ResizedImageField(
                blank=True,
                force_format="WEBP",
                quality=88,
                size=[1600, 900],
                upload_to="blog/covers/%Y/%m/",
            ),
        ),
        migrations.RenameField(
            model_name="blogpost",
            old_name="tags",
            new_name="legacy_tags",
        ),
        migrations.CreateModel(
            name="Tag",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=200, unique=True)),
            ],
            options={
                "verbose_name": "Blog tag",
                "verbose_name_plural": "Blog tags",
                "ordering": ("name",),
            },
        ),
        migrations.AddField(
            model_name="blogpost",
            name="tags",
            field=models.ManyToManyField(blank=True, related_name="posts", to="blog.tag"),
        ),
        migrations.RunPython(migrate_legacy_tags, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="blogpost",
            name="legacy_tags",
        ),
        migrations.CreateModel(
            name="BlogPostRating",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("score", models.PositiveSmallIntegerField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("post", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="customer_ratings", to="blog.blogpost")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="blog_post_ratings", to="accounts.customer")),
            ],
            options={"ordering": ("-updated_at",)},
        ),
        migrations.AddConstraint(
            model_name="blogpostrating",
            constraint=models.UniqueConstraint(fields=("post", "user"), name="blog_post_rating_once_per_customer"),
        ),
        migrations.AddConstraint(
            model_name="blogpostrating",
            constraint=models.CheckConstraint(condition=models.Q(("score__gte", 1), ("score__lte", 5)), name="blog_post_rating_score_1_5"),
        ),
        migrations.AlterModelOptions(
            name="blogpost",
            options={
                "ordering": ("-is_featured", "-published_at", "-created_at"),
                "permissions": (("vip", "VIP"), ("common", "COMMON")),
                "verbose_name": "Blog post",
                "verbose_name_plural": "Blog posts",
            },
        ),
    ]
