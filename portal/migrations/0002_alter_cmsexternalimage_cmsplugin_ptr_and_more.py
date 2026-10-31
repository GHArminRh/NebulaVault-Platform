# Historical no-op retained for compatibility with deployed migration records.
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("portal", "0001_initial")]
    operations = []
