from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("staff", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.AddField(
            model_name="staffuser",
            name="wagtail_groups",
            field=models.ManyToManyField(
                blank=True,
                db_table="accounts_staffuser_wagtail_groups",
                help_text="The Wagtail groups this staff user belongs to.",
                related_name="user_set",
                related_query_name="user",
                to="auth.group",
            ),
        ),
    ]
