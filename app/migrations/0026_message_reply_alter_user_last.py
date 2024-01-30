# Generated by Django 4.2.7 on 2024-01-16 11:39

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0025_mood_alter_user_last_user_mood'),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='reply',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='user',
            name='last',
            field=models.DateTimeField(blank=True, default=datetime.datetime(2024, 1, 16, 11, 39, 48, 759914, tzinfo=datetime.timezone.utc), null=True),
        ),
    ]
