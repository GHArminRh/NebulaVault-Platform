from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0003_email_two_factor_and_challenges")]

    operations = [
        migrations.AddField(
            model_name="customer",
            name="terms_accepted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="customer",
            name="terms_version",
            field=models.CharField(blank=True, max_length=32),
        ),
        migrations.AddField(
            model_name="customer",
            name="newsletter_opt_in",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="customer",
            name="newsletter_opt_in_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
