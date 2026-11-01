from django.db import migrations


def convert_default_homepage(apps, schema_editor):
    alias = schema_editor.connection.alias
    Page = apps.get_model("wagtailcore", "Page")
    HomePage = apps.get_model("sitecms", "HomePage")
    Site = apps.get_model("wagtailcore", "Site")
    ContentType = apps.get_model("contenttypes", "ContentType")

    # Wagtail's own initial-data migration creates this child of the root page.
    page = Page.objects.using(alias).filter(path="00010001").first()
    if page is None:
        raise RuntimeError(
            "Wagtail's initial homepage was not found; refusing to create a "
            "second page tree automatically."
        )

    homepage_type, _ = ContentType.objects.using(alias).get_or_create(
        app_label="sitecms",
        model="homepage",
        defaults={"name": "صفحه اصلی"},
    )

    if not HomePage.objects.using(alias).filter(pk=page.pk).exists():
        HomePage.objects.using(alias).create(
            page_ptr_id=page.pk,
            hero_eyebrow="فضای دیجیتال شما، با نظم تازه",
            hero_title="همه‌چیز سر جای خودش؛",
            hero_highlight="کنترل در دست شما.",
            hero_description=(
                "محصولات، خریدها، اشتراک‌ها و لایسنس‌ها را در یک تجربه‌ی امن "
                "و هماهنگ مدیریت کنید؛ ساده، شفاف و بدون شلوغی."
            ),
            hero_primary_cta_label="کشف محصولات",
            hero_primary_cta_url="#products",
            body="",
        )

    Page.objects.using(alias).filter(pk=page.pk).update(
        content_type_id=homepage_type.pk,
        title="صفحه اصلی نبیولا والت",
        slug="home",
    )

    # Repoint the built-in default Wagtail site to the existing page tree.
    existing_site = Site.objects.using(alias).filter(
        hostname="mydigigi.ir", port=80
    ).first()
    default_site = existing_site or Site.objects.using(alias).filter(
        is_default_site=True
    ).first()
    if default_site is None:
        default_site = Site.objects.using(alias).first()
    if default_site is None:
        raise RuntimeError("Wagtail did not create its initial Site record.")

    Site.objects.using(alias).exclude(pk=default_site.pk).update(
        is_default_site=False
    )
    default_site.hostname = "mydigigi.ir"
    default_site.port = 80
    default_site.root_page_id = page.pk
    default_site.is_default_site = True
    default_site.save(
        using=alias,
        update_fields=["hostname", "port", "root_page", "is_default_site"],
    )


class Migration(migrations.Migration):
    dependencies = [
        ("sitecms", "0001_initial"),
        ("wagtailcore", "0098_apitoken"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunPython(
            convert_default_homepage,
            migrations.RunPython.noop,
        ),
    ]
