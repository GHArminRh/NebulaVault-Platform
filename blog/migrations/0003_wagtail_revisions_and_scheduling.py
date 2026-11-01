import django.db.models.deletion
import modelcluster.fields
from django.db import migrations, models


def initialize_publication_state(apps, schema_editor):
    BlogPost = apps.get_model("blog", "BlogPost")
    alias = schema_editor.connection.alias
    for post in BlogPost.objects.using(alias).filter(status="published").iterator():
        published_at = post.published_at or post.created_at
        BlogPost.objects.using(alias).filter(pk=post.pk).update(
            live=True,
            first_published_at=published_at,
            last_published_at=published_at,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("blog", "0002_tags_uuid_resized_rating"),
        ("wagtailcore", "0098_apitoken"),
    ]

    operations = [
        migrations.AlterField(
            model_name="blogpost",
            name="tags",
            field=modelcluster.fields.ParentalManyToManyField(
                blank=True,
                related_name="posts",
                to="blog.tag",
            ),
        ),
        migrations.AddField(
            model_name="blogpost",
            name="live",
            field=models.BooleanField(default=False, editable=False, verbose_name="live"),
        ),
        migrations.AddField(
            model_name="blogpost",
            name="has_unpublished_changes",
            field=models.BooleanField(
                default=False,
                editable=False,
                verbose_name="has unpublished changes",
            ),
        ),
        migrations.AddField(
            model_name="blogpost",
            name="first_published_at",
            field=models.DateTimeField(
                blank=True,
                db_index=True,
                null=True,
                verbose_name="first published at",
            ),
        ),
        migrations.AddField(
            model_name="blogpost",
            name="last_published_at",
            field=models.DateTimeField(
                editable=False,
                null=True,
                verbose_name="last published at",
            ),
        ),
        migrations.AddField(
            model_name="blogpost",
            name="live_revision",
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="wagtailcore.revision",
                verbose_name="live revision",
            ),
        ),
        migrations.AddField(
            model_name="blogpost",
            name="go_live_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name="go live date/time",
            ),
        ),
        migrations.AddField(
            model_name="blogpost",
            name="expire_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name="expiry date/time",
            ),
        ),
        migrations.AddField(
            model_name="blogpost",
            name="expired",
            field=models.BooleanField(
                default=False,
                editable=False,
                verbose_name="expired",
            ),
        ),
        migrations.AddField(
            model_name="blogpost",
            name="latest_revision",
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="wagtailcore.revision",
                verbose_name="latest revision",
            ),
        ),
        migrations.RunPython(
            initialize_publication_state,
            migrations.RunPython.noop,
        ),
    ]
