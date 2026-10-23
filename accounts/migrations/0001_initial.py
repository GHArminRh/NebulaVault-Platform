# Initial customer model; Django's built-in auth.User remains the staff/admin model.
import django.utils.timezone
from django.db import migrations, models
import django.contrib.auth.validators
import django.contrib.auth.base_user


class Migration(migrations.Migration):
    initial = True
    dependencies = [("auth", "0012_alter_user_first_name_max_length")]
    operations = [
        migrations.CreateModel(
            name="Customer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("password", models.CharField(max_length=128, verbose_name="password")),
                ("last_login", models.DateTimeField(blank=True, null=True, verbose_name="last login")),
                ("email", models.EmailField(max_length=254, unique=True)),
                ("username", models.CharField(max_length=150, unique=True)),
                ("first_name", models.CharField(blank=True, max_length=150)),
                ("last_name", models.CharField(blank=True, max_length=150)),
                ("is_active", models.BooleanField(default=True)),
                ("date_joined", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-date_joined"], "verbose_name": "customer", "verbose_name_plural": "customers"},
            managers=[("objects", django.contrib.auth.base_user.BaseUserManager())],
        ),
    ]
