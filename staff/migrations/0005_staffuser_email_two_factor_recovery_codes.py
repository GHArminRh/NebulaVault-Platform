from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("staff", "0004_staffuser_avatar_two_factor"),
        ("accounts", "0003_email_two_factor_and_challenges"),
    ]

    operations = [
        migrations.AddField(
            model_name="staffuser",
            name="email_two_factor_enabled",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="staffuser",
            name="recovery_codes",
            field=models.JSONField(blank=True, default=list, editable=False),
        ),
    ]
