# Historical no-op retained so already-deployed databases keep their migration record.
from django.db import migrations


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = []
