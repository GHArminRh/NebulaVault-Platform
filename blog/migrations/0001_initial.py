from django.db import migrations, models
class Migration(migrations.Migration):
    initial = True
    dependencies = [("comment", "0001_initial")]
    operations = [
      migrations.CreateModel(name="BlogPost", fields=[
        ("id", models.AutoField(primary_key=True, serialize=False)),
        ("title", models.CharField(max_length=220)),
        ("slug", models.SlugField(blank=True,max_length=240,unique=True)),
        ("excerpt", models.CharField(blank=True,max_length=360)),
        ("content", models.TextField()),
        ("cover_image", models.ImageField(blank=True,upload_to="blog/covers/%Y/%m/")),
        ("category", models.CharField(blank=True,db_index=True,max_length=80)),
        ("tags", models.CharField(blank=True,help_text="Comma-separated keywords",max_length=240)),
        ("status", models.CharField(choices=[("draft","Draft"),("published","Published")],db_index=True,default="draft",max_length=12)),
        ("is_featured", models.BooleanField(db_index=True,default=False)),
        ("seo_title", models.CharField(blank=True,max_length=220)),
        ("seo_description", models.CharField(blank=True,max_length=320)),
        ("published_at", models.DateTimeField(blank=True,db_index=True,null=True)),
        ("created_at", models.DateTimeField(auto_now_add=True)),
        ("updated_at", models.DateTimeField(auto_now=True)),
      ],options={"ordering":("-is_featured","-published_at","-created_at"),"verbose_name":"Blog post","verbose_name_plural":"Blog posts"}),
    ]
