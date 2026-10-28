import django.db.models.deletion
from django.db import migrations, models
from django.conf import settings
import comment.models

class Migration(migrations.Migration):
    initial=True
    dependencies=[("accounts","0001_initial"),("contenttypes","0002_remove_content_type_name")]
    operations=[
      migrations.CreateModel(name="CommentSettings",fields=[
        ("name",models.CharField(default="Nebula Vault Blog",max_length=30)),
        ("slug",models.SlugField(default="default-config",primary_key=True,serialize=False)),
        ("content_words_count",models.PositiveSmallIntegerField(default=40)),
        ("status_check",models.BooleanField(default=True)),
        ("status_edited_check",models.BooleanField(default=True)),
        ("allow_spoiler",models.BooleanField(default=True)),
        ("allow_reply",models.BooleanField(default=True)),
        ("allow_edit",models.BooleanField(default=True)),
        ("allow_delete",models.BooleanField(default=True)),
        ("allow_reaction",models.BooleanField(default=True)),
        ("per_page",models.PositiveSmallIntegerField(default=10)),
        ("theme_direction",models.CharField(default="rtl",max_length=3)),
        ("theme_dark_mode",models.BooleanField(default=True)),
      ],options={"verbose_name":"Comment settings","verbose_name_plural":"Comment settings"}),
      migrations.CreateModel(name="React",fields=[
        ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),
        ("slug",models.CharField(max_length=20,unique=True)),
        ("emoji",models.CharField(max_length=5)),
      ]),
      migrations.CreateModel(name="Comment",fields=[
        ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),
        ("content_main",models.TextField()),
        ("content",models.TextField()),
        ("is_spoiler",models.BooleanField(default=False)),
        ("is_pinned",models.BooleanField(default=False)),
        ("status",models.CharField(choices=[("d","Pending review"),("a","Accepted"),("r","Rejected")],db_index=True,default="d",max_length=1)),
        ("status_edited",models.CharField(choices=[("n","None"),("d","Pending review"),("a","Accepted"),("r","Rejected")],default="n",max_length=1)),
        ("urlhash",models.CharField(default=comment.models.make_urlhash,editable=False,max_length=50,unique=True)),
        ("posted",models.DateTimeField(auto_now_add=True)),
        ("updated",models.DateTimeField(auto_now=True)),
        ("object_id",models.PositiveIntegerField()),
        ("content_type",models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,to="contenttypes.contenttype")),
        ("parent",models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.CASCADE,related_name="children",to="comment.comment")),
        ("user",models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name="comments",to="accounts.customer")),
      ],options={"ordering":("-is_pinned","-posted"),"verbose_name":"Comment","verbose_name_plural":"Comments"}),
      migrations.CreateModel(name="Reaction",fields=[
        ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),
        ("user",models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name="comment_reactions",to="accounts.customer")),
        ("comment",models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name="reactions",to="comment.comment")),
        ("react",models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name="reactions",to="comment.react")),
      ],options={"constraints":[models.UniqueConstraint(fields=("user","comment"),name="comment_one_reaction_per_user")]}),

      migrations.RunPython(
        lambda apps,schema_editor: (
          apps.get_model("comment","CommentSettings").objects.get_or_create(slug="default-config",defaults={"name":"Nebula Vault Blog"}),
          apps.get_model("comment","React").objects.get_or_create(slug="like",defaults={"emoji":"👍"}),
          apps.get_model("comment","React").objects.get_or_create(slug="dislike",defaults={"emoji":"👎"}),
        ), migrations.RunPython.noop),

    ]
