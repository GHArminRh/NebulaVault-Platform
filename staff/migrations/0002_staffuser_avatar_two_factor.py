import accounts.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("staff", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="staffuser",
            name="avatar",
            field=models.ImageField(blank=True, upload_to=accounts.validators.avatar_upload_to, validators=[accounts.validators.validate_avatar_size]),
        ),
        migrations.AddField(
            model_name="staffuser",
            name="two_factor_enabled",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="staffuser",
            name="two_factor_secret",
            field=models.CharField(blank=True, editable=False, max_length=255),
        ),
    ]
