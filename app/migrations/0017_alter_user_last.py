# Generated by Django 4.2.3 on 2023-10-23 22:39

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0016_alter_user_last'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='last',
            field=models.DateTimeField(blank=True, default=datetime.datetime(2023, 10, 23, 22, 39, 1, 881720, tzinfo=datetime.timezone.utc), null=True),
        ),
    ]